# State and commands

Python 3.10+ and Git are required. Run the script by its absolute plugin path;
pass the application's Git root with `--project`. The plugin never executes strings
from `tasks.json` as shell commands. The orchestrator selects/runs the actual checks.

```sh
python3 <plugin>/scripts/workflow.py config --project <repo>
python3 <plugin>/scripts/workflow.py init --project <repo> --task add-orders --title "Add orders"
python3 <plugin>/scripts/workflow.py status --project <repo> --task add-orders
```

Initialize Git for a new application first. The helper also supports an unborn
branch. It expects the repository root; use a separate workflow for submodules.
Keep `.dev-workflow/` ignored in the application before taking validation snapshots.
The helper does not modify the application's Git ignore rules automatically.

Fill the generated `spec.md` and `tasks.json` under
`.dev-workflow/tasks/<task>/`. Read [handoffs](handoffs.md) for the schema. The
orchestrator alone writes state. Agents can write distinct reports in that task
directory, without editing `state.json`. This avoids concurrent lost updates.

After the user explicitly approves the displayed specification:

```sh
python3 <plugin>/scripts/workflow.py approve --project <repo> --task add-orders --confirmed-by-user
python3 <plugin>/scripts/workflow.py task-done --project <repo> --task add-orders --item backend
python3 <plugin>/scripts/workflow.py advance --project <repo> --task add-orders
```

`approve` fingerprints the specification, task graph and effective configuration,
enters implementation and clears prior completion/evidence/repair counters. It is
only for a newly accepted plan revision, never to reset a failing task's budget.
Spec/config changes invalidate approval. Task completion requires its dependencies.
`advance` moves one stage and refuses incomplete tasks or stale required evidence.

Before each check get `fingerprint` from `status`. Save an actual result report
(e.g. `reports/tests.md`) inside the task directory, then record it:

```sh
python3 <plugin>/scripts/workflow.py record --project <repo> --task add-orders --kind tests --result pass --report reports/tests.md --fingerprint <fingerprint-before-checks>
```

Kinds are `tests`, `review`, `documentation`; results are `pass`, `fail`, `not-run`.
Reports include commands/exit codes or review evidence, required checks not run,
findings, and the checked code fingerprint. Empty reports are rejected. Their
content hashes are checked too: editing a report requires recording it again.

Snapshot fingerprints include tracked and nonignored untracked files, executable
bits and symlinks; they exclude `.dev-workflow/`. Git commit metadata is excluded,
so committing identical code does not invalidate checks. Ignored dependencies and
external services are not fingerprinted: record relevant versions in the report
and reassess when these change. Dirty/staged edits must be inspected on resume.

Any changed project file makes prior evidence stale. Reconcile it explicitly:
rerun affected checks and examine the changed review surface. For a docs-only
delta, a tester can retain previous runtime-test results after inspecting and
recording why the delta cannot affect them; run relevant doc/example checks.
Write a new report identifying old and new fingerprints, changed paths and reused
checks, and record against the new fingerprint. Never simply re-stamp old reports.
Reuse requires a saved snapshot/diff or Git reference that proves the delta from
the previously checked content. A whole-tree hash or current `git diff` alone
cannot reconstruct earlier uncommitted content. If that baseline is unavailable
after interruption, rerun the required checks and review rather than guessing.
Do the equivalent delta review with the independent reviewer. This preserves an
auditable decision without rerunning an unrelated full suite.

```sh
python3 <plugin>/scripts/workflow.py retry --project <repo> --task add-orders --problem auth-failure
```

Call `retry` before each repair round for a stable problem ID. The returned mode
requires orchestrator diagnosis on escalation; attempts beyond the configured
budget fail. Keep problem IDs stable instead of renaming failures to bypass it.

Save `delivery.json` with `fingerprint`, `commit`, `branch`, `base` and verified
`pr_url`, then advance from delivery to done. With the optional `delivery: local`
override, omit the PR URL but record the final local commit. Status works at any
stage and flags stale approval/evidence. On interruption stop scheduling, collect
active-agent results, inspect the tree, then resume only unfinished/invalidated work.

The JSON files are local audit aids, not authentication or a security boundary.
Never edit state manually to bypass a gate. Native tool results and the actual
user conversation remain the evidence for claims recorded here.
