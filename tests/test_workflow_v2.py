"""Exercise risk, authorization, evidence and delivery through the public v2 CLI."""

import copy
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest


SCRIPT = Path(__file__).resolve().parents[1] / "scripts" / "workflow.py"


class WorkflowV2Tests(unittest.TestCase):
    def setUp(self):
        temporary = tempfile.TemporaryDirectory()
        self.addCleanup(temporary.cleanup)
        self.project = Path(temporary.name) / "application"
        self.project.mkdir()
        self.environment = {
            **os.environ, "GIT_CONFIG_NOSYSTEM": "1",
            "GIT_CONFIG_GLOBAL": os.devnull, "GIT_TERMINAL_PROMPT": "0",
        }
        self.task_id = "change"
        self.git("init", "--quiet")
        self.git("config", "user.name", "Workflow test")
        self.git("config", "user.email", "workflow@example.invalid")
        self.git("config", "commit.gpgsign", "false")
        (self.project / ".gitignore").write_text(".dev-workflow/\n", encoding="utf-8")
        (self.project / "app.txt").write_text("source\n", encoding="utf-8")

    @property
    def task(self):
        return self.project / ".dev-workflow/tasks" / self.task_id

    def git(self, *arguments):
        result = subprocess.run(
            ["git", "-C", str(self.project), *arguments],
            env=self.environment, check=True, capture_output=True, text=True,
        )
        return result.stdout.strip()

    def cli(self, command, *arguments, error=None):
        result = subprocess.run(
            [sys.executable, str(SCRIPT), command, "--project", str(self.project),
             "--task", self.task_id, *arguments],
            env=self.environment, capture_output=True, text=True,
        )
        if error is not None:
            self.assertNotEqual(result.returncode, 0, result.stdout)
            self.assertIn(error, result.stderr)
            self.assertNotIn("Traceback", result.stderr)
            return result
        self.assertEqual(result.returncode, 0, result.stderr)
        return json.loads(result.stdout)

    def initialize(self, risk=None):
        options = ["--risk", risk] if risk else []
        state = self.cli("init", "--title", "Change behavior",
                         "--risk-reason", "Assessed the affected behavior", *options)
        (self.task / "spec.md").write_text(
            "# Change behavior\nImplement the accepted behavior and focused checks.\n",
            encoding="utf-8",
        )
        plan = [{
            "id": "work", "goal": "Change application behavior", "files": ["app.txt"],
            "depends_on": [], "contract": "", "acceptance": ["Expected behavior works"],
            "checks": ["python3 -m unittest"],
        }]
        (self.task / "tasks.json").write_text(json.dumps(plan), encoding="utf-8")
        return state

    def prepare_verification(self, risk="standard"):
        self.initialize(risk)
        flag = "--authorized-by-request" if risk == "low" else "--confirmed-by-user"
        self.cli("approve", flag)
        self.cli("task-done", "--item", "work")
        self.assertEqual(self.cli("advance")["stage"], "verification")

    @staticmethod
    def report(risk="standard"):
        roles = {"low": ["orchestrator"], "standard": ["reviewer"],
                 "high": ["tester", "reviewer"]}[risk]
        return {
            "implementer_ids": ["worker"],
            "checks": [{"command": "python3 -m unittest", "result": "pass", "exit_code": 0}],
            "assessments": {
                role: {"agent_id": role, "result": "pass", "summary": "Checked affected behavior"}
                for role in roles
            },
            "documentation": "No externally visible documentation changes are needed.",
            "blockers": [],
        }

    def record(self, report, result="pass", fingerprint=None, error=None):
        (self.task / "verification.json").write_text(json.dumps(report), encoding="utf-8")
        fingerprint = fingerprint or self.cli("status")["fingerprint"]
        return self.cli("record", "--kind", "verification", "--result", result,
                        "--report", "verification.json", "--fingerprint", fingerprint, error=error)

    def test_default_risk_requires_explicit_acceptance(self):
        state = self.initialize()
        self.assertEqual(state["schema_version"], 2)
        self.assertEqual(state["risk"], "standard")
        self.cli("advance", error="unapproved")
        self.cli("approve", error="Explicit user confirmation")
        self.cli("approve", "--authorized-by-request", error="Explicit user confirmation")
        self.assertEqual(self.cli("approve", "--confirmed-by-user")["stage"], "implementation")

    def test_low_request_authorization_keeps_risk_and_exact_spec(self):
        self.initialize("low")
        original = (self.task / "spec.md").read_bytes()
        self.cli("approve", error="Explicit user confirmation")
        state = self.cli("approve", "--authorized-by-request")
        self.assertEqual(state["risk"], "low")
        self.assertEqual(state["authorization"], "authorized-by-request")
        self.assertEqual((self.task / "spec.md").read_bytes(), original)
        self.cli("approve", "--confirmed-by-user", "--authorized-by-request",
                 error="mutually exclusive")
        state = self.cli("approve", "--confirmed-by-user")
        self.assertEqual(state["authorization"], "confirmed-by-user")

    def test_rationale_and_spec_are_required(self):
        self.initialize("low")
        self.cli("approve", "--authorized-by-request", "--risk-reason", "", error="risk-reason")
        (self.task / "spec.md").write_text("# Empty", encoding="utf-8")
        self.cli("approve", "--authorized-by-request", error="Write the specification")

    def test_each_risk_accepts_only_its_minimum_assessments(self):
        for risk in ("low", "standard", "high"):
            with self.subTest(risk=risk):
                self.task_id = risk
                self.prepare_verification(risk)
                self.cli("advance", error="verification evidence")
                report = self.report(risk)
                self.record(report)
                status = self.cli("status")
                self.assertEqual(set(status["required_assessments"]), set(report["assessments"]))
                self.assertTrue(status["approval_current"])
                self.assertTrue(status["current_evidence"]["verification"])
                self.assertEqual(self.cli("advance")["stage"], "delivery")

    def test_incomplete_or_failed_evidence_cannot_be_recorded_as_pass(self):
        self.prepare_verification()
        baseline = self.report()
        variants = [
            {"checks": []},
            {"checks": [{"command": "test", "result": "not-run", "exit_code": None}]},
            {"checks": [{"command": "test", "result": "fail", "exit_code": 1}]},
            {"checks": [{"command": "test", "result": "pass", "exit_code": 1}]},
            {"checks": [{"command": "test", "result": "pass", "exit_code": False}]},
            {"assessments": {}},
            {"assessments": {"reviewer": {
                "agent_id": "worker", "result": "pass", "summary": "Self review"}}},
            {"assessments": {"reviewer": {
                "agent_id": "reviewer", "result": "not-run", "summary": "Unavailable"}}},
            {"implementer_ids": []},
            {"implementer_ids": ["worker", "worker"]},
            {"documentation": ""},
            {"blockers": ["Required integration check is unavailable"]},
        ]
        for change in variants:
            with self.subTest(change=change):
                self.record({**baseline, **change}, error="")
                self.cli("advance", error="verification evidence")

    def test_high_risk_needs_two_independent_assessors(self):
        self.prepare_verification("high")
        report = self.report("high")
        report["assessments"].pop("tester")
        self.record(report, error="cannot support a passing result")
        report = self.report("high")
        report["assessments"]["tester"]["agent_id"] = "reviewer"
        self.record(report, error="distinct")
        report["assessments"]["tester"]["agent_id"] = "worker"
        self.record(report, error="distinct")

    def test_required_checks_from_every_task_must_be_recorded(self):
        self.initialize()
        path = self.task / "tasks.json"
        plan = json.loads(path.read_text(encoding="utf-8"))
        extra = {**plan[0], "id": "extra", "files": ["other.txt"],
                 "checks": ["python3 -m compileall ."]}
        path.write_text(json.dumps([*plan, extra]), encoding="utf-8")
        self.cli("approve", "--confirmed-by-user")
        for item in ("work", "extra"):
            self.cli("task-done", "--item", item)
        self.cli("advance")
        report = self.report()
        self.record(report, error="Missing required checks: python3 -m compileall .")
        report["checks"] = [{"command": "true", "result": "pass", "exit_code": 0}]
        self.record(report, error="Missing required checks")
        report["checks"] = self.report()["checks"] + [
            {"command": "python3 -m compileall .", "result": "pass", "exit_code": 0}]
        self.record(report)
        self.assertEqual(self.cli("advance")["stage"], "delivery")

    def test_explicit_failure_or_not_run_blocks_even_with_complete_report(self):
        self.prepare_verification()
        for result in ("fail", "not-run"):
            for report in ({}, self.report()):
                with self.subTest(result=result, report=report):
                    state = self.record(report, result=result)
                    self.assertEqual(state["evidence"]["verification"]["result"], result)
                    self.cli("advance", error="verification evidence")

    def test_code_and_report_edits_invalidate_recorded_evidence(self):
        self.prepare_verification()
        report = self.report()
        self.record(report)
        old = self.cli("status")["fingerprint"]
        modified = copy.deepcopy(report)
        modified["documentation"] = "Revised documentation assessment"
        (self.task / "verification.json").write_text(json.dumps(modified), encoding="utf-8")
        self.assertFalse(self.cli("status")["current_evidence"]["verification"])
        self.record(modified)
        self.assertEqual(self.cli("advance")["stage"], "delivery")
        (self.project / "app.txt").write_text("changed after checks\n", encoding="utf-8")
        self.assertFalse(self.cli("status")["current_evidence"]["verification"])
        self.cli("advance", error="verification evidence")
        self.record(modified, fingerprint=old, error="Code changed during checks")

    def test_reclassification_clears_evidence_without_resetting_same_plan_retries(self):
        self.prepare_verification("low")
        self.record(self.report("low"))
        self.cli("retry", "--problem", "failure")
        self.cli("approve", "--risk", "high", "--confirmed-by-user", error="fresh --risk-reason")
        self.cli("approve", "--risk", "high", "--risk-reason", "Authorization is affected",
                 "--authorized-by-request", error="explicit user confirmation")
        state = self.cli("approve", "--risk", "high", "--risk-reason", "Authorization is affected",
                         "--confirmed-by-user")
        self.assertEqual(state["risk"], "high")
        self.assertEqual(state["completed_tasks"], [])
        self.assertEqual(state["evidence"], {})
        self.assertEqual(state["attempts"]["failure"], 1)
        self.assertEqual(self.cli("approve", "--confirmed-by-user")["attempts"]["failure"], 1)
        self.assertEqual(self.cli("status")["required_assessments"], ["tester", "reviewer"])

    def test_downgrading_authorized_risk_needs_explicit_confirmation(self):
        self.initialize("high")
        self.cli("approve", "--confirmed-by-user")
        self.cli("approve", "--risk", "low", "--risk-reason", "Reduced scope",
                 "--authorized-by-request", error="explicit user confirmation")
        self.assertEqual(self.cli("status")["risk"], "high")
        self.cli("approve", "--risk", "low", "--risk-reason", "Reduced scope",
                 "--confirmed-by-user")
        self.assertEqual(self.cli("status")["risk"], "low")

    def test_cross_version_evidence_and_request_authorization_are_rejected(self):
        self.prepare_verification()
        (self.task / "legacy.md").write_text("Legacy report", encoding="utf-8")
        fingerprint = self.cli("status")["fingerprint"]
        for kind in ("tests", "review", "documentation"):
            self.cli("record", "--kind", kind, "--result", "pass", "--report", "legacy.md",
                     "--fingerprint", fingerprint, error="V2 tasks")
        # Build an old task fixture; production must never migrate task state manually.
        state = json.loads((self.task / "state.json").read_text())
        state["schema_version"] = 1
        state["stage"] = "analysis"
        (self.task / "state.json").write_text(json.dumps(state), encoding="utf-8")
        self.cli("approve", "--authorized-by-request", error="explicit user acceptance")
        self.cli("approve", "--confirmed-by-user")
        self.cli("record", "--kind", "verification", "--result", "pass", "--report", "legacy.md",
                 "--fingerprint", fingerprint, error="V1 tasks")

    def test_v2_delivery_resumes_and_requires_current_commit_and_pr_when_needed(self):
        for mode in ("local", "draft-pr"):
            with self.subTest(mode=mode):
                self.task_id = mode
                config = self.project / ".dev-workflow/config.json"
                config.parent.mkdir(exist_ok=True)
                config.write_text(json.dumps({"delivery": mode}), encoding="utf-8")
                self.prepare_verification()
                self.record(self.report())
                resumed = self.cli("status")
                self.assertEqual(resumed["stage"], "verification")
                self.assertTrue(resumed["current_evidence"]["verification"])
                self.assertEqual(self.cli("advance")["stage"], "delivery")
                self.git("add", ".")
                self.git("commit", "--quiet", "--allow-empty", "-m", "Implement feature")
                delivery = {
                    "fingerprint": self.cli("status")["fingerprint"],
                    "commit": self.git("rev-parse", "HEAD"), "branch": "feature", "base": "main",
                }
                path = self.task / "delivery.json"
                if mode == "draft-pr":
                    path.write_text(json.dumps(delivery), encoding="utf-8")
                    self.cli("advance", error="verified draft PR URL")
                    delivery["pr_url"] = "https://github.com/owner/repo/pull/1"
                path.write_text(json.dumps({**delivery, "commit": "wrong"}), encoding="utf-8")
                self.cli("advance", error="Delivery commit must match HEAD")
                path.write_text(json.dumps({**delivery, "fingerprint": "old"}), encoding="utf-8")
                self.cli("advance", error="Stale delivery record")
                path.write_text(json.dumps(delivery), encoding="utf-8")
                self.assertEqual(self.cli("advance")["stage"], "done")
                self.assertEqual(self.cli("status")["stage"], "done")
                self.cli("advance", error="Cannot advance this stage")


if __name__ == "__main__":
    unittest.main()
