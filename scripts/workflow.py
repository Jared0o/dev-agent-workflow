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
STAGES = ("analysis", "implementation", "tests", "review", "documentation", "delivery", "done")
ROLES = {"orchestrator", "implementer", "tester", "reviewer", "documenter"}


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


def config(project):
    data = read_json(PLUGIN / "config/defaults.json")
    override = project / ".dev-workflow/config.json"
    if override.exists():
        merge(data, read_json(override))
    require(data["schema_version"] == 1, "Unsupported config version")
    require(set(data["models"]) == ROLES, "Invalid model roles")
    for role in data["models"].values():
        require(set(role) == {"model", "effort"}, "Each role needs model and effort")
        require(isinstance(role["model"], str) and re.fullmatch(r"[A-Za-z0-9._-]+", role["model"]),
                "Invalid model identifier")
        require(role["effort"] in {"low", "medium", "high", "xhigh", "max", "ultra"},
                "Invalid reasoning effort; actual model support must be checked in Codex")
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


def load_state(directory):
    state = read_json(directory / "state.json")
    require(isinstance(state, dict) and state.get("schema_version") == 1
            and state.get("stage") in STAGES, "Invalid or unsupported state")
    require(isinstance(state.get("completed_tasks"), list)
            and isinstance(state.get("evidence"), dict)
            and isinstance(state.get("attempts"), dict), "Invalid state collections")
    return state


def approved(project, directory, state):
    return state.get("approval") == approval_digest(project, directory)


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


def run(args):
    project = Path(args.project).resolve()
    if args.command == "config":
        return config(project)
    project = project_root(project)
    directory = task_dir(project, args.task)
    path = directory / "state.json"
    if args.command == "init":
        require(not directory.exists(), "Task already exists; use status/resume")
        state = {"schema_version": 1, "task_id": args.task, "title": args.title,
                 "stage": "analysis", "approval": None, "completed_tasks": [],
                 "evidence": {}, "attempts": {}, "baseline": fingerprint(project)}
        write_json(path, state)
        write_json(directory / "tasks.json", [])
        (directory / "spec.md").write_text(f"# {args.title}\n", encoding="utf-8")
        return {"directory": str(directory), **state}
    state = load_state(directory)
    current = fingerprint(project)
    if args.command == "status":
        try:
            valid = approved(project, directory, state)
            issue = None
        except (ValueError, OSError) as error:
            valid, issue = False, str(error)
        return {**state, "fingerprint": current, "approval_current": valid,
                "plan_issue": issue, "current_evidence": {
                    kind: evidence_valid(directory, state, kind, current)
                    for kind in ("tests", "review", "documentation")}}
    if args.command == "approve":
        require(args.confirmed_by_user, "Record approval only after explicit user acceptance")
        state.update(approval=approval_digest(project, directory), stage="implementation",
                     completed_tasks=[], evidence={}, attempts={})
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
            return {"attempt": count, "mode": "ordinary" if count <= settings["repair_rounds"]
                    else "orchestrator-diagnosis-required"}
        elif args.command == "advance":
            stage = state["stage"]
            require(stage not in {"analysis", "done"}, "Cannot advance this stage")
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
            state["stage"] = STAGES[STAGES.index(stage) + 1]
    write_json(path, state)
    return state


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("command", choices=("config", "init", "status", "approve", "task-done", "record", "retry", "advance"))
    parser.add_argument("--project", required=True)
    parser.add_argument("--task")
    parser.add_argument("--title")
    parser.add_argument("--confirmed-by-user", action="store_true")
    parser.add_argument("--item")
    parser.add_argument("--kind", choices=("tests", "review", "documentation"))
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
