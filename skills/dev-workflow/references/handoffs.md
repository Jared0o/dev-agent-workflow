# Analysis and handoffs

Keep `spec.md` focused on the problem, scope/exclusions, architecture decisions,
contracts (links to their source), acceptance scenarios and validation commands.
Include migrations and compatibility only when relevant. Do not copy the repo.
Record the exact authorized revision, not a paraphrase of an earlier proposal.
For v2 include risk, execution mode and their rationales. A single owner needs only one task entry;
do not invent a graph or contract for work that does not need one.

`tasks.json` is an array. Each task has this shape:

```json
[
  {
    "id": "backend",
    "goal": "Implement the agreed endpoint",
    "files": ["internal/orders/", "internal/orders_test.go"],
    "depends_on": [],
    "contract": "api/openapi.yaml",
    "acceptance": ["Unauthenticated requests are rejected"],
    "checks": ["go test ./internal/orders/..."]
  }
]
```

For v2, `checks` contains exact repository command strings, including any needed
working-directory change (for example `cd web && npm test`). Every listed command
must appear with a passing result in verification; include repository-required
checks when preparing the plan. The helper compares strings, not shell semantics.
V1 retains its existing freeform check descriptions.

Use relative file names or directory prefixes ending `/`; no globs, absolute paths
or traversal. `contract` is a link/string, empty when no contract applies.
Dependencies are task IDs in this plan and must be acyclic. Overlapping file scopes
require a dependency ordering; broad scopes reduce safe parallelism. Scopes are
coordination boundaries, not OS sandboxes. Check actual changed files on return.
Contract/generator/lockfile work should be a prerequisite task if consumers depend
on it. An agent encountering necessary out-of-scope work reports it first.

The orchestrator's spawn prompt contains:

- Role instruction from `roles.md` and explicit effective helper model/effort for the task risk.
- Goal, task ID, authorized spec excerpt, risk, contract reference and owned files.
- Necessary context references and the acceptance/check lists.
- A statement that workers share the workspace, must preserve others' edits and
  may not delegate, change Git branches, commit or publish.
- Required reply: `status`, `changed_files`, `checks` (command/result),
  `findings_or_blockers`, `artifact_paths`, plus actual model/effort and usage if exposed.

Use a fresh context (`fork_turns=none`, or the runtime's equivalent) when selecting
a worker model. If the runtime requires shared history to preserve a tool capability,
disclose the limitation rather than assuming model overrides worked. Do not send
implementer conclusions as the expected answer to the tester/reviewer; send actual
command evidence so checks can be reused when still valid. V2 workers return
results for the orchestrator's single verification report, not mandatory separate
stage reports.

Only on an explicit user request for architecture consultation, send a separate
read-only prompt using `architecture_model` from effective config. Include the
design question, constraints and relevant references; request recommendations,
alternatives, consequences and unknowns. Record the orchestrator's conclusions
in `spec.md` before implementation. A proposed or accepted plan alone does not
trigger consultation, and its result cannot satisfy required verification.

On return, verify file scope and dependencies, retain a short result, record a
completed implementation task, then dispatch newly unblocked tasks. Workers never
mark their own stage as accepted. If a question changes the spec or task graph,
pause affected work and reapprove before continuing.
