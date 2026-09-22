# State and commands

Python 3.10+ and Git are required. Run the helper by its absolute plugin path with
the application's Git root as `--project`. Initialize Git for new applications.
Keep `.dev-workflow/` ignored; the helper does not change Git ignore rules.
Only the orchestrator writes state. Commands do not execute shell strings from
tasks or reports.

## New tasks (v2)

```sh
python3 <plugin>/scripts/workflow.py config --project <repo>
python3 <plugin>/scripts/workflow.py init --project <repo> --task add-orders --title "Add orders" --risk standard --risk-reason "Changes application behavior without high-risk boundaries"
python3 <plugin>/scripts/workflow.py status --project <repo> --task add-orders
```

Risk defaults to `standard`; record a meaningful reason before approval. Write the
short `spec.md` and `tasks.json` in `.dev-workflow/tasks/<task>/` using
[handoffs](handoffs.md). Include the classification and rationale in the displayed
plan. One task entry suffices for one implementation owner.

After explicit acceptance of that plan, or an already accepted exact revision:

```sh
python3 <plugin>/scripts/workflow.py approve --project <repo> --task add-orders --confirmed-by-user
```

For `low` only, a clear request to perform the work can authorize it without another
pause: use `approve --authorized-by-request` instead. These flags are mutually
exclusive. Neither risk selection nor a request only for analysis is authorization.

Use `approve --risk high --risk-reason "<new rationale>" --confirmed-by-user`
to record an explicitly accepted reclassification. Reclassifying an already
authorized task requires explicit confirmation, including lowering its risk.
Pause dependent work until any needed acceptance is obtained.
Risk, execution mode and their reasons are fingerprinted with spec, tasks and
effective config.
Approval clears previous completion and evidence; never use reapproval to recycle
a failed task's repair budget.

```sh
python3 <plugin>/scripts/workflow.py task-done --project <repo> --task add-orders --item backend
python3 <plugin>/scripts/workflow.py advance --project <repo> --task add-orders
```

Task completion requires its dependencies. The v2 sequence is
`analysis → implementation → verification → delivery → done`. Documentation is
part of implementation, not a separate stage. `advance` refuses incomplete work
or missing, failed or stale required evidence.

## Direct execution for trivial low-risk work

`init` and `approve` accept `--execution-mode delegated|direct-low` and
`--execution-reason "<rationale>"`. New tasks default to `delegated`. For an
unambiguous text or cosmetic change, select `direct-low` with `--risk low` and a
nonempty reason. Approval requires one task without dependencies. Logic, security,
data or contract changes do not qualify, even if they fit in one line.

The main session implements, runs focused and repository-required checks, and
assesses the diff. Record its actual ID as the sole `implementer_ids` entry and
as `assessments.orchestrator.agent_id`. Keep the normal stages and report.

Change modes through `approve --execution-mode <mode> --execution-reason "<reason>"`
with a fresh rationale and the applicable authorization flag. This clears completion and
evidence without replenishing repairs. Raising risk also requires `delegated` and
the existing explicit reclassification acceptance. Old v2 states without mode
fields remain delegated and keep their original approval digest shape; a mode
change is explicit. Changing effective config still invalidates prior approval.
`status` reports the mode and effective helper models; `config --risk high` shows
the high-risk override without changing state. `config` also exposes the separate
`architecture_model` setting for consultation explicitly requested by the user.
It does not add a role to `effective_models` or change required assessments.

## One verification report

Collect actual command results and assessments into `reports/verification.json`.
For example, this standard-risk report shape requires an independent reviewer:

```json
{
  "implementer_ids": ["worker-1"],
  "checks": [
    {"command": "python3 -m unittest discover -s tests -v", "result": "pass", "exit_code": 0}
  ],
  "assessments": {
    "reviewer": {
      "agent_id": "reviewer-1",
      "result": "pass",
      "summary": "Reviewed the integrated code and documentation; no blocking findings."
    }
  },
  "documentation": "Updated README.md for the new behavior.",
  "blockers": []
}
```

List the actual implementing agents, all required commands, results and exit codes.
Every command in the approved tasks' `checks` must appear verbatim in the report's
`checks[].command`; extra relevant commands are allowed. The helper rejects a pass
when an approved command is omitted. Select actual commands while preparing the
plan, rather than descriptive labels. Include non-root working directories in the
command itself and run it from the agreed project root.
Use `not-run` and a null exit code for unavailable checks. Include missing required
work in blockers; use the documentation field for changed docs or a justification
that no update is needed. Keep nonblocking findings, limitations and reuse
justifications in assessment summaries, referring to full logs when helpful.

Required assessments are `orchestrator` for low, `reviewer` for standard, and
`tester` plus `reviewer` for high. In `delegated`, assessors must differ from
implementers. Only `direct-low` requires the orchestrator to be the sole
implementer and assessor.
When switching from direct to delegated execution, retain every actual implementer
ID, including prior main-session edits. If the main session is among them, a fresh
configured reviewer performs the low-risk assessment; record that independent
agent's actual ID under `assessments.orchestrator`.
The high-risk tester and reviewer must differ from each other. Use actual runtime
agent identifiers (including the main agent for the low-risk assessment).
Every listed check must pass with exit code zero and required assessments must
pass with no blockers to record an overall pass. Failed or unperformed verification
can be recorded before the report is complete.

Before checks obtain `fingerprint` from `status`, then record the observed outcome:

```sh
python3 <plugin>/scripts/workflow.py record --project <repo> --task add-orders --kind verification --result pass --report reports/verification.json --fingerprint <fingerprint-before-checks>
```

The report hash and code fingerprint must still match when advancing. Editing the
report requires recording it again. Helpers validate recorded structure and
identity separation; they cannot prove that a command ran, an independent agent
participated or a human approved. Never manufacture evidence to satisfy a gate.

## Reuse and interruption

Fingerprints include tracked and nonignored untracked files, executable bits and
symlinks, excluding `.dev-workflow/` and commit metadata. Committing identical code
does not invalidate checks. Submodules require separate workflows. Ignored
dependencies and external services are not captured: record relevant versions and
reassess results when those change.

Any project-file change makes recorded evidence stale. Rerun affected checks and
assess the delta, then update the single report with old/new fingerprints, changed
paths, reused results and their justification. Use a saved snapshot/diff or Git
reference that reconstructs the checked baseline. A hash or current `git diff`
alone cannot reconstruct earlier uncommitted content. If that baseline is missing
after interruption, rerun required checks and assessment rather than guessing.

A documentation-only delta can reuse runtime results after the required assessor
reviews its impact; check affected executable examples/docs. No separate tester
is needed below high risk. Reviewers use valid existing test evidence instead of
automatically rerunning it.

Save state at stage boundaries and before stopping. On interruption collect
active results, inspect dirty/staged work and resume only unfinished or invalidated
work. Keep full logs in the ignored artifact directory and handoffs concise.

## Repairs and delivery

```sh
python3 <plugin>/scripts/workflow.py retry --project <repo> --task add-orders --problem auth-failure
```

Record a retry before each repair round using a stable problem ID. Respect the
configured ordinary/diagnosed attempt limits; exhausted problems remain blockers.
An escalated v2 `retry` retains `mode: orchestrator-diagnosis-required` and also
returns `diagnosis_model` from config. Spawn that model for focused read-only
diagnosis before the diagnosed attempt; send its correction to the implementer.
For direct work, switch to delegated mode before this repair. Diagnosis is not
verification, does not clear blockers and does not extend the retry budget.
Spec/config changes require a newly accepted revision, not an excuse to reset
attempts. Never edit state manually to bypass a gate.

Follow [delivery](delivery.md). Save `delivery.json` with `fingerprint`, `commit`,
`branch`, `base` and a verified `pr_url`, then advance to done. For `delivery: local`,
omit the PR URL but retain the final local commit. Publication failure preserves
local work in delivery.

Existing `schema_version: 1` tasks use the [legacy stages and reports](legacy-v1.md).
The configuration schema remains version 1; it is separate from task-state v2.
