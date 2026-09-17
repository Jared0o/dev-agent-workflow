"""Exercise the public helper CLI against isolated, offline Git repositories."""

import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest


SCRIPT = Path(__file__).resolve().parents[1] / "scripts" / "workflow.py"


class WorkflowTests(unittest.TestCase):
    def setUp(self):
        self.temporary = tempfile.TemporaryDirectory()
        self.addCleanup(self.temporary.cleanup)
        self.root = Path(self.temporary.name)
        self.project = self.root / "application"
        self.project.mkdir()
        self.environment = {
            **os.environ,
            "GIT_CONFIG_NOSYSTEM": "1",
            "GIT_CONFIG_GLOBAL": os.devnull,
            "GIT_TERMINAL_PROMPT": "0",
        }
        self.git("init", "--quiet")
        self.git("config", "user.name", "Workflow test")
        self.git("config", "user.email", "workflow@example.invalid")
        self.git("config", "commit.gpgsign", "false")
        (self.project / ".gitignore").write_text(".dev-workflow/\n", encoding="utf-8")
        (self.project / "app.txt").write_text("initial application\n", encoding="utf-8")
        self.task = self.project / ".dev-workflow/tasks/add-feature"

    def git(self, *arguments):
        result = subprocess.run(
            ["git", "-C", str(self.project), *arguments],
            capture_output=True, text=True, env=self.environment, check=True,
        )
        return result.stdout.strip()

    def cli(self, command, *arguments, error=None, project=None):
        result = subprocess.run(
            [sys.executable, str(SCRIPT), command, "--project",
             str(project or self.project), "--task", "add-feature", *arguments],
            capture_output=True, text=True, env=self.environment,
        )
        if error is not None:
            self.assertNotEqual(result.returncode, 0, result.stdout)
            self.assertIn(error, result.stderr)
            self.assertNotIn("Traceback", result.stderr)
            return result
        self.assertEqual(result.returncode, 0, result.stderr)
        return json.loads(result.stdout)

    @staticmethod
    def item(name="backend", files=None, dependencies=None):
        return {
            "id": name, "goal": "Implement the approved application feature",
            "files": files or [name + "/"], "depends_on": dependencies or [],
            "contract": "", "acceptance": ["The specified behavior works"],
            "checks": ["Run the relevant application tests"],
        }

    def initialize(self, plan=None):
        state = self.cli("init", "--title", "Add feature")
        # Most historical assertions deliberately exercise retained v1 artifacts.
        legacy = self.task / "state.json"
        data = json.loads(legacy.read_text(encoding="utf-8"))
        data["schema_version"] = 1
        data.pop("risk", None)
        data.pop("risk_reason", None)
        data.pop("plan_digest", None)
        data.pop("execution_mode", None)
        data.pop("execution_reason", None)
        legacy.write_text(json.dumps(data), encoding="utf-8")
        (self.task / "spec.md").write_text(
            "# Add feature\nImplement the agreed behavior with appropriate tests.\n",
            encoding="utf-8",
        )
        self.write_plan(plan if plan is not None else [self.item()])
        return state

    def write_plan(self, plan):
        (self.task / "tasks.json").write_text(json.dumps(plan), encoding="utf-8")

    def override(self, data):
        directory = self.project / ".dev-workflow"
        directory.mkdir(exist_ok=True)
        (directory / "config.json").write_text(json.dumps(data), encoding="utf-8")

    def approve(self):
        return self.cli("approve", "--confirmed-by-user")

    def prepare_tests(self):
        self.initialize()
        self.approve()
        self.cli("task-done", "--item", "backend")
        self.assertEqual(self.cli("advance")["stage"], "tests")

    def record(self, kind="tests", result="pass", fingerprint=None, error=None):
        report = self.task / "reports" / (kind + ".md")
        report.parent.mkdir(exist_ok=True)
        report.write_text("Executed checks and inspected results: " + result, encoding="utf-8")
        snapshot = fingerprint or self.cli("status")["fingerprint"]
        return self.cli("record", "--kind", kind, "--result", result,
                        "--report", "reports/" + report.name,
                        "--fingerprint", snapshot, error=error)

    def test_init_supports_unborn_repository_and_requires_approval(self):
        state = self.initialize()
        self.assertEqual(state["stage"], "analysis")
        self.assertFalse(self.cli("status")["approval_current"])
        self.cli("task-done", "--item", "backend", error="unapproved")
        self.cli("advance", error="unapproved")
        self.cli("approve", error="explicit user acceptance")
        self.assertEqual(self.approve()["stage"], "implementation")
        self.cli("init", "--title", "Again", error="Task already exists")

    def test_status_explains_incomplete_analysis(self):
        self.cli("init", "--title", "Add feature")
        status = self.cli("status")
        self.assertFalse(status["approval_current"])
        self.assertIsNotNone(status["plan_issue"])
        self.assertFalse(any(status["current_evidence"].values()))

    def test_project_must_be_git_root(self):
        nested = self.project / "nested"
        nested.mkdir()
        self.cli("init", "--title", "Feature", project=nested, error="repository root")

    def test_unknown_and_duplicate_task_ids_rejected(self):
        self.initialize()
        for plan, message in [
            ([self.item(dependencies=["missing"])], "Unknown dependency"),
            ([self.item(), self.item()], "Duplicate task ID"),
        ]:
            with self.subTest(message=message):
                self.write_plan(plan)
                self.cli("approve", "--confirmed-by-user", error=message)

    def test_cycles_rejected_at_multiple_depths(self):
        self.initialize()
        for plan in [
            [self.item("a", dependencies=["a"])],
            [self.item("a", dependencies=["b"]), self.item("b", dependencies=["a"])],
            [self.item("root", dependencies=["a"]), self.item("a", dependencies=["b"]),
             self.item("b", dependencies=["c"]), self.item("c", dependencies=["a"])],
        ]:
            with self.subTest(plan=plan):
                self.write_plan(plan)
                self.cli("approve", "--confirmed-by-user", error="Cyclic dependencies")

    def test_overlapping_scopes_require_ordering(self):
        self.initialize()
        for left, right in [("src/", "src/app.py"), ("src/", "src/nested/"),
                            ("app.py", "app.py")]:
            with self.subTest(left=left, right=right):
                self.write_plan([self.item("a", [left]), self.item("b", [right])])
                self.cli("approve", "--confirmed-by-user", error="Overlapping scopes")

    def test_transitive_ordering_allows_overlap(self):
        self.initialize([
            self.item("a", ["src/"]), self.item("b", ["bridge.py"], ["a"]),
            self.item("c", ["src/app.py"], ["b"]),
        ])
        self.approve()
        self.cli("task-done", "--item", "c", error="Dependencies are incomplete")
        for name in ("a", "b", "c"):
            self.cli("task-done", "--item", name)
        self.assertEqual(self.cli("advance")["stage"], "tests")

    def test_similar_directory_names_do_not_overlap(self):
        self.initialize([self.item("a", ["src/"]), self.item("b", ["src-other/"])])
        self.approve()

    def test_unsafe_scopes_rejected(self):
        self.initialize()
        for scope in ("../outside", "/absolute", "src/../secret", "./app.py",
                      "src//file", "src\\file", "src/*.py", ".git/config",
                      ".dev-workflow/state.json", "src/[ab].py", "src/?.py"):
            with self.subTest(scope=scope):
                self.write_plan([self.item(files=[scope])])
                self.cli("approve", "--confirmed-by-user", error="Invalid file scope")

    def test_config_overrides_merge_and_invalid_values_fail(self):
        self.override({"models": {"implementer": {"model": "custom-coder"}}})
        data = self.cli("config")
        self.assertEqual(data["models"]["implementer"]["model"], "custom-coder")
        self.assertEqual(data["models"]["implementer"]["effort"], "medium")
        self.override({"risk_model_overrides": {"high": {"reviewer": {"effort": "medium"}}},
                       "escalation_model": {"model": "custom-diagnoser"},
                       "models": {"reviewer": {"model": "custom-reviewer"}}})
        data = self.cli("config", "--risk", "high")
        self.assertEqual(data["effective_models"]["reviewer"],
                         {"model": "gpt-6-astra", "effort": "medium"})
        self.assertEqual(data["models"]["reviewer"]["model"], "custom-reviewer")
        self.assertEqual(data["escalation_model"], {"model": "custom-diagnoser", "effort": "high"})
        for override, message in [
            ({"unknown": True}, "Unknown config field"),
            ({"max_parallel_agents": True}, "Invalid max_parallel_agents"),
            ({"max_parallel_agents": 0}, "Invalid max_parallel_agents"),
            ({"repair_rounds": 9}, "Invalid repair_rounds"),
            ({"models": {"tester": {"model": "bad model"}}}, "Invalid model identifier"),
            ({"models": {"tester": {"effort": "extreme"}}}, "Invalid reasoning effort"),
            ({"delivery": "publish"}, "Invalid delivery mode"),
            ({"schema_version": 2}, "Unsupported config version"),
            ({"escalation_model": {"model": "bad model"}}, "Invalid model identifier"),
            ({"escalation_model": {"effort": "extreme"}}, "Invalid reasoning effort"),
            ({"risk_model_overrides": {"high": {"reviewer": {"effort": "extreme"}}}},
             "Invalid reasoning effort"),
            ({"risk_model_overrides": {"standard": {}}}, "Unknown config field"),
        ]:
            with self.subTest(override=override):
                self.override(override)
                self.cli("config", error=message)

    def test_spec_task_and_config_edits_invalidate_approval(self):
        self.initialize()
        self.approve()
        (self.task / "spec.md").write_text("# Different explicitly approved requirements\n", encoding="utf-8")
        self.assertFalse(self.cli("status")["approval_current"])
        self.cli("advance", error="reapprove")
        self.approve()
        self.write_plan([self.item("frontend")])
        self.assertFalse(self.cli("status")["approval_current"])
        self.approve()
        self.override({"delivery": "local"})
        self.assertFalse(self.cli("status")["approval_current"])

    def test_reapproval_clears_prior_results(self):
        self.prepare_tests()
        self.record()
        self.cli("retry", "--problem", "test-failure")
        (self.task / "spec.md").write_text("# User accepted a revised implementation scope\n", encoding="utf-8")
        state = self.approve()
        self.assertEqual(state["stage"], "implementation")
        self.assertEqual(state["completed_tasks"], [])
        self.assertEqual(state["evidence"], {})
        self.assertEqual(state["attempts"], {})

    def test_incomplete_or_unknown_tasks_cannot_pass(self):
        self.initialize()
        self.approve()
        self.cli("advance", error="Implementation tasks are incomplete")
        self.cli("task-done", "--item", "missing", error="Unknown implementation task")
        self.cli("task-done", "--item", "backend")
        state = self.cli("task-done", "--item", "backend")
        self.assertEqual(state["completed_tasks"], ["backend"])

    def test_missing_failed_and_not_run_evidence_block_progress(self):
        self.prepare_tests()
        self.cli("advance", error="tests evidence")
        for outcome in ("fail", "not-run"):
            with self.subTest(outcome=outcome):
                self.record(result=outcome)
                self.assertFalse(self.cli("status")["current_evidence"]["tests"])
                self.cli("advance", error="tests evidence")
        self.record()
        self.assertEqual(self.cli("advance")["stage"], "review")
        self.cli("advance", error="review evidence")

    def test_source_edits_invalidate_checks_but_not_plan(self):
        self.prepare_tests()
        self.record()
        old = self.cli("status")["fingerprint"]
        (self.project / "app.txt").write_text("changed application\n", encoding="utf-8")
        state = self.cli("status")
        self.assertNotEqual(state["fingerprint"], old)
        self.assertTrue(state["approval_current"])
        self.assertFalse(state["current_evidence"]["tests"])
        self.cli("advance", error="stale tests evidence")
        self.record(fingerprint=old, error="Code changed during checks")

    def test_report_edits_and_deletion_invalidate_evidence(self):
        self.prepare_tests()
        self.record()
        report = self.task / "reports/tests.md"
        report.write_text("Changed report", encoding="utf-8")
        self.assertFalse(self.cli("status")["current_evidence"]["tests"])
        self.cli("advance", error="tests evidence")
        self.record()
        report.unlink()
        self.assertFalse(self.cli("status")["current_evidence"]["tests"])

    def test_evidence_report_must_be_separate_nonempty_and_inside_task(self):
        self.prepare_tests()
        fingerprint = self.cli("status")["fingerprint"]
        (self.task / "empty.md").touch()
        for name, message in [("spec.md", "separate evidence report"),
                              ("empty.md", "Empty evidence report"),
                              ("../../../../app.txt", "inside the task directory")]:
            with self.subTest(name=name):
                self.cli("record", "--kind", "tests", "--result", "pass",
                         "--report", name, "--fingerprint", fingerprint, error=message)

    def test_symlink_report_cannot_escape_task_directory(self):
        self.prepare_tests()
        (self.task / "escape.md").symlink_to(self.project / "app.txt")
        self.cli("record", "--kind", "tests", "--result", "pass", "--report", "escape.md",
                 "--fingerprint", self.cli("status")["fingerprint"], error="inside the task directory")

    def test_symlink_task_directory_cannot_escape_project(self):
        external = self.root / "external"
        external.mkdir()
        (self.project / ".dev-workflow").symlink_to(external, target_is_directory=True)
        self.cli("init", "--title", "Feature", error="Task directory escapes project")
        self.assertEqual(list(external.iterdir()), [])

    def test_symlink_state_output_is_not_overwritten(self):
        self.initialize()
        external = self.root / "original-state.json"
        state = self.task / "state.json"
        original = state.read_text(encoding="utf-8")
        external.write_text(original, encoding="utf-8")
        state.unlink()
        state.symlink_to(external)
        self.cli("approve", "--confirmed-by-user", error="Refusing symlink output")
        self.assertEqual(external.read_text(encoding="utf-8"), original)

    def test_fingerprint_captures_modes_deletions_untracked_and_symlinks(self):
        self.initialize()
        self.git("add", "app.txt", ".gitignore")
        previous = self.cli("status")["fingerprint"]
        app = self.project / "app.txt"
        app.chmod(0o755)
        current = self.cli("status")["fingerprint"]
        self.assertNotEqual(current, previous)
        app.unlink()
        deleted = self.cli("status")["fingerprint"]
        self.assertNotEqual(deleted, current)
        (self.project / "new.txt").write_text("new source", encoding="utf-8")
        added = self.cli("status")["fingerprint"]
        self.assertNotEqual(added, deleted)
        link = self.project / "source-link"
        link.symlink_to("new.txt")
        linked = self.cli("status")["fingerprint"]
        self.assertNotEqual(linked, added)
        link.unlink()
        link.symlink_to("missing.txt")
        self.assertNotEqual(self.cli("status")["fingerprint"], linked)

    def test_artifacts_and_git_commit_do_not_change_code_fingerprint(self):
        self.prepare_tests()
        before = self.cli("status")["fingerprint"]
        self.record()
        (self.task / "notes.md").write_text("Worker notes", encoding="utf-8")
        self.git("add", ".")
        self.git("commit", "--quiet", "-m", "Initial application")
        self.assertEqual(self.cli("status")["fingerprint"], before)
        self.assertTrue(self.cli("status")["current_evidence"]["tests"])

    def test_staging_and_committing_deleted_file_preserves_snapshot(self):
        self.initialize()
        self.git("add", ".")
        self.git("commit", "--quiet", "-m", "Initial application")
        (self.project / "app.txt").unlink()
        deleted = self.cli("status")["fingerprint"]
        self.git("add", "--all")
        self.assertEqual(self.cli("status")["fingerprint"], deleted)
        self.git("commit", "--quiet", "-m", "Remove application file")
        self.assertEqual(self.cli("status")["fingerprint"], deleted)

    def test_retry_escalation_and_exhaustion_are_persistent(self):
        self.initialize()
        self.approve()
        for attempt, mode in [(1, "ordinary"), (2, "ordinary"),
                              (3, "orchestrator-diagnosis-required")]:
            result = self.cli("retry", "--problem", "test-failure")
            self.assertEqual(result, {"attempt": attempt, "mode": mode})
        self.cli("retry", "--problem", "test-failure", error="Repair budget exhausted")
        self.assertEqual(self.cli("status")["attempts"]["test-failure"], 3)
        self.assertEqual(self.cli("retry", "--problem", "other-failure")["attempt"], 1)

    def test_legacy_approval_rejects_execution_modes(self):
        self.initialize()
        self.cli("approve", "--confirmed-by-user", "--execution-mode", "direct-low",
                 "--execution-reason", "Text only", error="only supported for v2")

    def reach_delivery(self):
        self.prepare_tests()
        for kind, next_stage in [("tests", "review"), ("review", "documentation"),
                                 ("documentation", "delivery")]:
            self.record(kind)
            self.assertEqual(self.cli("advance")["stage"], next_stage)
        self.git("add", ".")
        self.git("commit", "--quiet", "-m", "Implement feature")
        return {"fingerprint": self.cli("status")["fingerprint"],
                "commit": self.git("rev-parse", "HEAD"), "branch": "feature/add-feature",
                "base": "main"}

    def test_complete_local_workflow_requires_matching_final_commit(self):
        self.override({"delivery": "local"})
        delivery = self.reach_delivery()
        self.cli("advance", error="delivery.json")
        path = self.task / "delivery.json"
        path.write_text(json.dumps({**delivery, "commit": "wrong"}), encoding="utf-8")
        self.cli("advance", error="Delivery commit must match HEAD")
        path.write_text(json.dumps({**delivery, "fingerprint": "old"}), encoding="utf-8")
        self.cli("advance", error="Stale delivery record")
        path.write_text(json.dumps(delivery), encoding="utf-8")
        self.assertEqual(self.cli("advance")["stage"], "done")
        self.assertEqual(self.cli("status")["stage"], "done")
        self.cli("advance", error="Cannot advance this stage")

    def test_draft_pr_mode_requires_github_pull_request_url(self):
        delivery = self.reach_delivery()
        path = self.task / "delivery.json"
        for url in (None, "https://github.com/owner/repo", "https://other.example/owner/repo/pull/1"):
            with self.subTest(url=url):
                path.write_text(json.dumps({**delivery, "pr_url": url}), encoding="utf-8")
                self.cli("advance", error="verified draft PR URL")
        path.write_text(json.dumps({**delivery, "pr_url": "https://github.com/owner/repo/pull/1"}),
                        encoding="utf-8")
        self.assertEqual(self.cli("advance")["stage"], "done")


if __name__ == "__main__":
    unittest.main()
