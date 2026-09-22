#!/usr/bin/env python3
"""Local artifacts for native-agent workflows; no model calls or shell execution."""

import argparse
import hashlib
import json
import os
from pathlib import Path
import re
import subprocess
import sys
import tempfile


PLUGIN = Path(__file__).resolve().parents[1]
V1_STAGES = ("analysis", "implementation", "tests", "review", "documentation", "delivery", "done")
V2_STAGES = ("analysis", "implementation", "verification", "delivery", "done")
ROLES = {"orchestrator", "implementer", "tester", "reviewer", "documenter"}
RISKS = {"low", "standard", "high"}
EXECUTION_MODES = {"delegated", "direct-low"}


def require(condition, message):
    if not condition:
        raise ValueError(message)


def read_json(path):
    return json.loads(path.read_text(encoding="utf-8"))


def write_json(path, data):
    path.parent.mkdir(parents=True, exist_ok=True)
    require(not path.is_symlink(), f"Refusing symlink output: {path}")
    fd, temporary = tempfile.mkstemp(dir=path.parent, prefix=".workflow-")
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as stream:
            json.dump(data, stream, indent=2, ensure_ascii=False)
            stream.write("\n")
        os.replace(temporary, path)
    finally:
        if os.path.exists(temporary):
            os.unlink(temporary)


def identifier(value):
    require(isinstance(value, str) and re.fullmatch(r"[a-z0-9][a-z0-9-]{0,63}", value),
            "IDs must be 1-64 lowercase letters, digits or hyphens")
    return value


def merge(base, override):
    require(isinstance(override, dict), "Config override must be an object")
    for key, value in override.items():
        require(key in base, f"Unknown config field: {key}")
        if isinstance(base[key], dict):
            merge(base[key], value)
        else:
            base[key] = value
    return base


def validate_model(role):
    require(isinstance(role, dict) and set(role) == {"model", "effort"},
            "Each role needs model and effort")
    require(isinstance(role["model"], str) and re.fullmatch(r"[A-Za-z0-9._-]+", role["model"]),
            "Invalid model identifier")
    require(isinstance(role["effort"], str)
            and role["effort"] in {"low", "medium", "high", "xhigh", "max", "ultra"},
            "Invalid reasoning effort; actual model support must be checked in Codex")


def role_models(settings, risk):
    return {**settings["models"], **settings["risk_model_overrides"].get(risk, {})}


def config(project):
    data = read_json(PLUGIN / "config/defaults.json")
    override = project / ".dev-workflow/config.json"
    if override.exists():
        merge(data, read_json(override))
    require(data["schema_version"] == 1, "Unsupported config version")
    require(set(data["models"]) == ROLES, "Invalid model roles")
    for role in data["models"].values():
        validate_model(role)
    require(set(data["risk_model_overrides"]) == {"high"}
            and set(data["risk_model_overrides"]["high"]) == {"reviewer"},
            "Risk model overrides support only the high-risk reviewer")
    validate_model(data["risk_model_overrides"]["high"]["reviewer"])
    validate_model(data["escalation_model"])
    validate_model(data["architecture_model"])
    for key in ("max_parallel_agents", "repair_rounds", "escalated_attempts"):
        require(type(data[key]) is int and 1 <= data[key] <= 8, f"Invalid {key}")
    require(data["communication_language"] == "pl" and data["working_language"] == "en",
            "This version supports Polish communication and English handoffs")
    require(data["delivery"] in {"draft-pr", "local"}, "Invalid delivery mode")
    return data


def git(project, *args):
    result = subprocess.run(["git", "-C", str(project), *args], capture_output=True)
    require(result.returncode == 0, result.stderr.decode(errors="replace").strip())
    return result.stdout


def project_root(project):
    project = project.resolve()
    root = Path(os.fsdecode(git(project, "rev-parse", "--show-toplevel")).strip()).resolve()
    require(root == project, "--project must be the Git repository root")
    return project


def fingerprint(project):
    """Hash current tracked + nonignored untracked files, without following symlinks."""
    files = set(git(project, "ls-files", "--cached", "--others", "--exclude-standard", "-z").split(b"\0"))
    digest = hashlib.sha256()
    for name in sorted(files - {b""}):
        if name == b".dev-workflow" or name.startswith(b".dev-workflow/"):
            continue
        path = project / os.fsdecode(name)
        require(path.parent.resolve().is_relative_to(project), "File parent escapes project")
        if not path.exists() and not path.is_symlink():
            continue
        digest.update(name + b"\0")
        if path.is_symlink():
            content = b"link:" + os.fsencode(os.readlink(path))
        elif path.is_dir():
            raise ValueError(f"Submodules/nested Git directories need separate workflows: {path}")
        else:
            content = str(path.stat().st_mode & 0o777).encode() + b":" + path.read_bytes()
        digest.update(hashlib.sha256(content).digest())
    return digest.hexdigest()


def task_dir(project, task):
    directory = project / ".dev-workflow/tasks" / identifier(task)
    require(directory.resolve().is_relative_to(project), "Task directory escapes project")
    return directory


def text_list(value, label, nonempty=True):
    require(isinstance(value, list) and (value or not nonempty)
            and all(isinstance(x, str) and x.strip() for x in value), f"Invalid {label}")


def tasks(directory):
    plan = read_json(directory / "tasks.json")
    require(isinstance(plan, list) and plan, "Provide at least one implementation task")
    ids = set()
    for task in plan:
        require(isinstance(task, dict) and set(task) == {
            "id", "goal", "files", "depends_on", "contract", "acceptance", "checks"},
            "Task fields: id, goal, files, depends_on, contract, acceptance, checks")
        task_id = identifier(task["id"])
        require(task_id not in ids, "Duplicate task ID")
        ids.add(task_id)
        require(isinstance(task["goal"], str) and task["goal"].strip(), "Missing task goal")
        require(isinstance(task["contract"], str), "Contract must be a string")
        for field in ("files", "acceptance", "checks", "depends_on"):
            text_list(task[field], field, nonempty=field != "depends_on")
        for name in task["files"]:
            parts = name.rstrip("/").split("/")
            require(not any(p in {"", ".", "..", ".git", ".dev-workflow"} for p in parts)
                    and not any(c in name for c in "\\*?[]"), "Invalid file scope")
    graph = {t["id"]: set(t["depends_on"]) for t in plan}
    require(all(deps <= ids for deps in graph.values()), "Unknown dependency")
    ancestors = {}

    def visit(node, pending):
        require(node not in pending, "Cyclic dependencies")
        if node not in ancestors:
            ancestors[node] = set(graph[node])
            for dep in graph[node]:
                ancestors[node].update(visit(dep, pending | {node}))
        return ancestors[node]

    for node in graph:
        visit(node, set())
    for index, left in enumerate(plan):
        for right in plan[index + 1:]:
            overlap = any(a.rstrip("/") == b.rstrip("/")
                          or (a.endswith("/") and b.startswith(a))
                          or (b.endswith("/") and a.startswith(b))
                          for a in left["files"] for b in right["files"])
            require(not overlap or left["id"] in ancestors[right["id"]]
                    or right["id"] in ancestors[left["id"]],
                    f"Overlapping scopes need ordered dependencies: {left['id']}, {right['id']}")
    return plan


def approval_digest(project, directory):
    spec = (directory / "spec.md").read_text(encoding="utf-8")
    require(len(spec.strip()) >= 20, "Write the specification before approval")
    data = {"spec": spec, "tasks": tasks(directory), "config": config(project)}
    return hashlib.sha256(json.dumps(data, sort_keys=True).encode()).hexdigest()


def validate_execution(risk, mode, reason, directory=None):
    require(isinstance(mode, str) and mode in EXECUTION_MODES, "Invalid execution mode")
    require(reason is None or isinstance(reason, str), "Invalid execution reason")
    if mode == "direct-low":
        require(risk == "low", "direct-low requires low risk")
        require(isinstance(reason, str) and reason.strip(),
                "direct-low requires a nonempty --execution-reason")
        if directory is not None:
            plan = tasks(directory)
            require(len(plan) == 1 and not plan[0]["depends_on"],
                    "direct-low requires one implementation task without dependencies")


def v2_approval_digest(project, directory, risk, reason, mode=None, execution_reason=None):
    require(risk in RISKS, "Invalid risk")
    require(isinstance(reason, str) and reason.strip(),
            "A nonempty --risk-reason is required for approval")
    data = {"plan": approval_digest(project, directory), "risk": risk, "risk_reason": reason}
    # Missing mode retains the digest shape of pre-update v2 states.
    require(mode is not None or execution_reason is None, "Execution reason requires an execution mode")
    validate_execution(risk, "delegated" if mode is None else mode, execution_reason, directory)
    if mode is not None:
        data.update(execution_mode=mode, execution_reason=execution_reason)
    return hashlib.sha256(json.dumps(data, sort_keys=True).encode()).hexdigest()


def load_state(directory):
    state = read_json(directory / "state.json")
    require(isinstance(state, dict), "Invalid or unsupported state")
    version = state.get("schema_version")
    stages = V1_STAGES if version == 1 else V2_STAGES
    require(type(version) is int and version in {1, 2} and state.get("stage") in stages,
            "Invalid or unsupported state")
    require(isinstance(state.get("completed_tasks"), list)
            and isinstance(state.get("evidence"), dict)
            and isinstance(state.get("attempts"), dict), "Invalid state collections")
    if version == 2:
        require(state.get("risk") in RISKS
                and (state.get("risk_reason") is None or isinstance(state["risk_reason"], str)),
                "Invalid v2 risk state")
        validate_execution(state["risk"], state.get("execution_mode", "delegated"),
                           state.get("execution_reason"))
    return state


def approved(project, directory, state):
    if state["schema_version"] == 1:
        expected = approval_digest(project, directory)
    else:
        expected = v2_approval_digest(project, directory, state["risk"], state["risk_reason"],
                                      state.get("execution_mode"), state.get("execution_reason"))
    return state.get("approval") == expected


def report_file(directory, name):
    path = (directory / name).resolve()
    require(path.is_relative_to(directory.resolve()) and path.is_file(),
            "Evidence must be an existing file inside the task directory")
    require(path.name not in {"state.json", "spec.md", "tasks.json"}, "Use a separate evidence report")
    require(path.stat().st_size > 0, "Empty evidence report")
    return path


def evidence_valid(directory, state, kind, current):
    item = state["evidence"].get(kind, {})
    if item.get("result") != "pass" or item.get("fingerprint") != current:
        return False
    try:
        report = report_file(directory, item["report"])
        return hashlib.sha256(report.read_bytes()).hexdigest() == item["report_hash"]
    except (OSError, ValueError, KeyError):
        return False


def required_roles(risk):
    return {"low": ("orchestrator",), "standard": ("reviewer",),
            "high": ("tester", "reviewer")}[risk]


def verification_result(data, risk, execution_mode="delegated"):
    require(execution_mode in EXECUTION_MODES, "Invalid execution mode")
    require(execution_mode != "direct-low" or risk == "low", "direct-low requires low risk")
    require(isinstance(data, dict), "Verification report must be a JSON object")
    implementers = data.get("implementer_ids")
    text_list(implementers, "implementer_ids")
    require(len(set(implementers)) == len(implementers),
            "implementer_ids must be unique")
    checks = data.get("checks")
    require(isinstance(checks, list) and checks, "checks must be a nonempty list")
    outcomes = []
    for check in checks:
        require(isinstance(check, dict) and set(check) == {"command", "result", "exit_code"}
                and isinstance(check["command"], str) and check["command"].strip()
                and check["result"] in {"pass", "fail", "not-run"}
                and (type(check["exit_code"]) is int or check["exit_code"] is None),
                "Invalid verification check")
        if check["result"] == "pass":
            require(check["exit_code"] == 0, "Passing checks need exit_code 0")
        outcomes.append(check["result"])

    assessments = data.get("assessments")
    require(isinstance(assessments, dict), "assessments must be an object")
    for role, assessment in assessments.items():
        require(role in {"orchestrator", "tester", "reviewer"}
                and isinstance(assessment, dict)
                and set(assessment) == {"agent_id", "result", "summary"}
                and isinstance(assessment["agent_id"], str) and assessment["agent_id"].strip()
                and assessment["result"] in {"pass", "fail", "not-run"}
                and isinstance(assessment["summary"], str) and assessment["summary"].strip(),
                "Invalid verification assessment")
        outcomes.append(assessment["result"])

    documentation = data.get("documentation")
    require(isinstance(documentation, str) and documentation.strip(),
            "documentation must be a nonempty string")
    blockers = data.get("blockers")
    text_list(blockers, "blockers", nonempty=False)
    roles = required_roles(risk)
    missing = [role for role in roles if role not in assessments]
    if missing:
        outcomes.append("not-run")
    if execution_mode == "direct-low":
        require(len(implementers) == 1, "direct-low requires exactly one implementer")
        if "orchestrator" in assessments:
            require(assessments["orchestrator"]["agent_id"] == implementers[0],
                    "direct-low orchestrator must be the implementer")
    for role in roles:
        if role in assessments and execution_mode != "direct-low":
            require(assessments[role]["agent_id"] not in implementers,
                    f"{role} must be distinct from implementers")
    if risk == "high" and not missing:
        require(assessments["tester"]["agent_id"] != assessments["reviewer"]["agent_id"],
                "tester and reviewer must be distinct")
    if blockers or "fail" in outcomes:
        return "fail"
    return "not-run" if "not-run" in outcomes else "pass"


def run(args):
    project = Path(args.project).resolve()
    require(args.command in {"init", "approve"}
            or (args.execution_mode is None and args.execution_reason is None),
            "Execution options are only supported by init and approve")
    if args.command == "config":
        settings = config(project)
        return {**settings, "effective_models": role_models(settings, args.risk or "standard")}
    project = project_root(project)
    directory = task_dir(project, args.task)
    path = directory / "state.json"
    if args.command == "init":
        require(not directory.exists(), "Task already exists; use status/resume")
        validate_execution(args.risk or "standard", args.execution_mode or "delegated",
                           args.execution_reason)
        state = {"schema_version": 2, "task_id": args.task, "title": args.title,
                 "stage": "analysis", "approval": None, "completed_tasks": [],
                 "evidence": {}, "attempts": {}, "baseline": fingerprint(project),
                 "risk": args.risk or "standard", "risk_reason": args.risk_reason,
                 "plan_digest": None, "authorization": None,
                 "execution_mode": args.execution_mode or "delegated",
                 "execution_reason": args.execution_reason}
        write_json(path, state)
        write_json(directory / "tasks.json", [])
        (directory / "spec.md").write_text(f"# {args.title}\n", encoding="utf-8")
        return {"directory": str(directory), **state}
    state = load_state(directory)
    current = fingerprint(project)
    v2 = state["schema_version"] == 2
    if args.command == "status":
        try:
            valid = approved(project, directory, state)
            issue = None
        except (ValueError, OSError) as error:
            valid, issue = False, str(error)
        kinds = ("verification",) if v2 else ("tests", "review", "documentation")
        result = {**state, "fingerprint": current, "approval_current": valid,
                  "plan_issue": issue, "current_evidence": {
                      kind: evidence_valid(directory, state, kind, current) for kind in kinds}}
        if v2:
            result["required_assessments"] = list(required_roles(state["risk"]))
            result["execution_mode"] = state.get("execution_mode", "delegated")
            result["execution_reason"] = state.get("execution_reason")
            result["effective_models"] = role_models(config(project), state["risk"])
        return result

    if args.command == "approve":
        require(not (args.confirmed_by_user and args.authorized_by_request),
                "Approval flags are mutually exclusive")
        if not v2:
            require(args.confirmed_by_user, "Record approval only after explicit user acceptance")
            require(args.risk is None and args.risk_reason is None,
                    "Risk classification is only supported for v2 tasks")
            require(args.execution_mode is None and args.execution_reason is None,
                    "Execution modes are only supported for v2 tasks")
            state.update(approval=approval_digest(project, directory), stage="implementation",
                         completed_tasks=[], evidence={}, attempts={})
        else:
            risk = args.risk or state["risk"]
            reason = args.risk_reason if args.risk_reason is not None else state["risk_reason"]
            mode = args.execution_mode if args.execution_mode is not None else state.get("execution_mode")
            execution_reason = (args.execution_reason if args.execution_reason is not None
                                else state.get("execution_reason"))
            if mode is None and args.execution_reason is not None:
                mode = "delegated"
            if args.execution_mode is not None and mode != state.get("execution_mode", "delegated"):
                require(args.execution_reason is not None and args.execution_reason.strip(),
                        "Execution mode changes require a fresh --execution-reason")
            if risk != state["risk"]:
                require(args.risk_reason is not None and args.risk_reason.strip(),
                        "Risk changes require a fresh --risk-reason")
                require(state.get("approval") is None or args.confirmed_by_user,
                        "Reclassifying an authorized task requires explicit user confirmation")
            require(args.confirmed_by_user or (risk == "low" and args.authorized_by_request),
                    "Explicit user confirmation is required unless low risk is authorized by request")
            approval = v2_approval_digest(project, directory, risk, reason, mode, execution_reason)
            plan_digest = approval_digest(project, directory)
            # A risk-only or repeated approval must not replenish the repair budget.
            execution_changed = (mode != state.get("execution_mode")
                                 or execution_reason != state.get("execution_reason"))
            attempts = (state["attempts"] if execution_changed
                        or state.get("plan_digest") == plan_digest else {})
            state.update(risk=risk, risk_reason=reason, plan_digest=plan_digest,
                         approval=approval, stage="implementation", completed_tasks=[],
                         evidence={}, attempts=attempts,
                         authorization="confirmed-by-user" if args.confirmed_by_user
                         else "authorized-by-request")
            if mode is not None:
                state.update(execution_mode=mode, execution_reason=execution_reason)
    else:
        require(approved(project, directory, state), "Plan/config changed or is unapproved; reapprove")
        if args.command == "task-done":
            plan = {t["id"]: t for t in tasks(directory)}
            require(args.item in plan, "Unknown implementation task")
            require(set(plan[args.item]["depends_on"]) <= set(state["completed_tasks"]),
                    "Dependencies are incomplete")
            if args.item not in state["completed_tasks"]:
                state["completed_tasks"].append(args.item)
        elif args.command == "record":
            require(args.fingerprint == current, "Code changed during checks; inspect and rerun affected checks")
            if v2:
                require(args.kind == "verification", "V2 tasks only accept verification reports")
                report = report_file(directory, args.report)
                report_data = read_json(report)
                require(isinstance(report_data, dict), "Verification report must be a JSON object")
                if args.result == "pass":
                    require(verification_result(report_data, state["risk"],
                                                state.get("execution_mode", "delegated")) == "pass",
                            "Verification report cannot support a passing result")
                    required_checks = {command for task in tasks(directory) for command in task["checks"]}
                    recorded_checks = {check["command"] for check in report_data["checks"]}
                    require(required_checks <= recorded_checks,
                            "Missing required checks: " + ", ".join(sorted(required_checks - recorded_checks)))
            else:
                require(args.kind in {"tests", "review", "documentation"},
                        "V1 tasks only accept legacy report kinds")
                report = report_file(directory, args.report)
            state["evidence"][args.kind] = {
                "result": args.result, "fingerprint": current,
                "report": str(report.relative_to(directory.resolve())),
                "report_hash": hashlib.sha256(report.read_bytes()).hexdigest()}
        elif args.command == "retry":
            problem = identifier(args.problem)
            count = state["attempts"].get(problem, 0) + 1
            settings = config(project)
            require(count <= settings["repair_rounds"] + settings["escalated_attempts"],
                    "Repair budget exhausted; report blocker to user")
            state["attempts"][problem] = count
            write_json(path, state)
            result = {"attempt": count, "mode": "ordinary" if count <= settings["repair_rounds"]
                      else "orchestrator-diagnosis-required"}
            if v2 and count > settings["repair_rounds"]:
                result["diagnosis_model"] = settings["escalation_model"]
            return result
        elif args.command == "advance":
            stage = state["stage"]
            stages = V2_STAGES if v2 else V1_STAGES
            require(stage not in {"analysis", "done"}, "Cannot advance this stage")
            if v2:
                needed = ("verification",) if stage in {"verification", "delivery"} else ()
            else:
                needed = {"tests": ("tests",), "review": ("tests", "review"),
                          "documentation": ("tests", "review", "documentation"),
                          "delivery": ("tests", "review", "documentation")}.get(stage, ())
            require({t["id"] for t in tasks(directory)} <= set(state["completed_tasks"]),
                    "Implementation tasks are incomplete")
            for kind in needed:
                require(evidence_valid(directory, state, kind, current),
                        f"Missing, failed or stale {kind} evidence")
            if stage == "delivery":
                delivered = read_json(directory / "delivery.json")
                require(delivered.get("fingerprint") == current, "Stale delivery record")
                if config(project)["delivery"] == "draft-pr":
                    require(isinstance(delivered.get("pr_url"), str) and re.fullmatch(
                        r"https://github\.com/[^/\s]+/[^/\s]+/pull/[0-9]+", delivered["pr_url"]),
                        "Record the verified draft PR URL")
                require(delivered.get("commit") == git(project, "rev-parse", "HEAD").decode().strip(),
                        "Delivery commit must match HEAD")
            state["stage"] = stages[stages.index(stage) + 1]
    write_json(path, state)
    return state


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("command", choices=(
        "config", "init", "status", "approve", "task-done", "record", "retry", "advance"))
    parser.add_argument("--project", required=True)
    parser.add_argument("--task")
    parser.add_argument("--title")
    parser.add_argument("--risk", choices=sorted(RISKS),
                        help="Risk for init (default: standard) or reclassification at approve")
    parser.add_argument("--risk-reason")
    parser.add_argument("--execution-mode", choices=sorted(EXECUTION_MODES))
    parser.add_argument("--execution-reason")
    parser.add_argument("--confirmed-by-user", action="store_true")
    parser.add_argument("--authorized-by-request", action="store_true")
    parser.add_argument("--item")
    parser.add_argument("--kind", choices=("tests", "review", "documentation", "verification"))
    parser.add_argument("--result", choices=("pass", "fail", "not-run"))
    parser.add_argument("--report")
    parser.add_argument("--fingerprint")
    parser.add_argument("--problem")
    args = parser.parse_args()
    required = {"init": ("task", "title"), "record": ("task", "kind", "result", "report", "fingerprint"),
                "task-done": ("task", "item"), "retry": ("task", "problem")}
    for name in required.get(args.command, () if args.command == "config" else ("task",)):
        if not getattr(args, name):
            parser.error(f"--{name} is required for {args.command}")
    try:
        print(json.dumps(run(args), indent=2, ensure_ascii=False))
    except (ValueError, OSError, KeyError, TypeError) as error:
        print(f"workflow: {error}", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
