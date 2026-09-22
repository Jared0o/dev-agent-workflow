---
name: dev-workflow
description: Implement applications and features with risk-based planning, native agents, focused verification and resumable delivery. Use for this development workflow, including status and resume requests; ordinary factual questions do not need it.
---

# Dev workflow

You are the orchestrator. Keep user discussion and summaries in Polish and concise
agent handoffs in English. User instructions and existing authorization prevail.

## Start or resume

1. Resolve the plugin root (two directories above this skill). Run
   `scripts/workflow.py config --project <root>` to read effective model, parallelism,
   repair and delivery settings. The main session is the orchestrator: respect the
   user-selected model and effort. The configured orchestrator (Sol / medium by
   default) is only a launch recommendation; the skill cannot switch the session.
   For v2 use `effective_models` for helpers (`config --risk <risk>` or task
   `status`); v1 keeps the base `models` roles.
   If a requested helper model/effort or native delegation is unavailable, preserve
   progress and request a replacement choice rather than silently substituting.
2. Inspect applicable AGENTS.md, Git status, manifests and relevant entrypoints.
   Read only matching [technology profiles](references/profiles/). For new apps,
   establish architecture/tooling and initialize Git before using the helper.
3. Read [state and commands](references/state.md). On resume, reconcile saved work
   with current changes before scheduling agents. Existing v1 tasks retain the
   [legacy workflow](references/legacy-v1.md); never migrate them implicitly.
4. For new work, classify risk below and initialize a v2 task. Record a short spec,
   risk rationale, acceptance scenarios and required checks. One implementation
   task is enough for one owner; split only for useful independent work. Read
   [handoffs](references/handoffs.md) when delegating and
   [delivery](references/delivery.md) before implementation to establish the branch
   and intended destination.
5. Consult `architecture_model` (Astra / high by default) only when the user
   explicitly asks for an architecture consultation. A suggested plan, request for
   analysis, or acceptance of a plan does not authorize it. Give the consultant
   the relevant constraints and design question for read-only assessment. The
   consultant returns recommendations, alternatives, consequences and unknowns;
   the orchestrator records its conclusions in `spec.md` and obtains any needed
   plan acceptance before implementation. This consultation never replaces the
   risk-required tester/reviewer assessments or repository checks.

## Choose the required verification

| Risk | Criteria | Helpers for one implementation task |
|---|---|---|
| `low` | Plain documentation, cosmetic UI, or an unambiguous local fix with no security, persistent-data or contract impact | Direct orchestrator execution for trivial changes; otherwise one implementer; orchestrator checks the result |
| `standard` | Other understood work without high-risk triggers; the default | One implementer and one independent reviewer |
| `high` | Authentication, authorization, payments, migrations, destructive operations or public API compatibility | One implementer, independent tester and independent reviewer |

Inspect uncertain impact before classifying; file count is not a risk measure.
A clear user request authorizes low-risk work without another approval pause.
Record request authorization explicitly; selecting `low` alone is not approval.

Choose `direct-low` only for an unambiguous text, ordinary documentation or cosmetic
UI change with no logic, security, data or contract impact. Inspect context first;
file count and `low` classification alone do not establish triviality. Record the
execution mode and reason with one implementation task without dependencies.
Other low-risk work uses `delegated`. Both paths retain focused checks and all
repository-required checks; do not add tests that only mirror a text replacement.
For standard/high work, present the plan and wait for explicit acceptance unless
the user already accepted that exact plan. A request to only analyze never
authorizes implementation, even at low risk.

## Execute

1. **Implementation, tests and documentation.** Delegate to one configured
   implementer in `delegated` mode. In `direct-low`, implement directly in the main
   session and use its actual runtime ID as the implementer. The implementing
   agent runs focused required checks and updates relevant documentation before
   verification; do not spawn a documenter for v2.
   Parallelize only independent scopes within `max_parallel_agents` and runtime
   limits. Shared contracts, generated files and lockfiles have one owner.
2. **Verification.** Integrate changes and use observed check results for the current
   code. At low risk, inspect the diff and evidence yourself. If you contributed
   implementation before switching to `delegated`, retain all implementer IDs and
   delegate the low-risk assessment to a fresh configured reviewer; record its
   actual ID under `assessments.orchestrator`. At standard risk,
   use a fresh configured reviewer (Sol / medium by default). At high risk, use
   a fresh tester for acceptance coverage and affected integrations, then a
   distinct reviewer with the high-risk override (Astra / high by default).
   Read only the assigned section in [roles](references/roles.md). Neither role
   repeats an unchanged passing suite without a concrete reason.
3. **Delivery.** Aggregate one verification report using the state reference,
   including documentation changes or why none are needed. Finish only when the
   risk-required assessments and repository-required checks pass. Follow delivery
   instructions; there is no separate documentation stage in v2.

## Repairs and resumption

- After fixes, rerun affected checks and review the delta plus relevant context.
  Reuse earlier results only with a provable baseline and a short justification;
  follow the state reference. Missing required checks are not passes.
- If a direct task proves nontrivial, switch to `delegated` with a fresh execution
  reason before continuing. If new information increases risk, also update the
  classification and required verification. Pause dependent work for any newly
  required user acceptance or
  material scope/contract change. Reapproval is for an accepted plan revision,
  never a way to reset a failing task's repair budget.
- Use configured repair limits (two ordinary rounds and one diagnosed attempt by
  default). Before an escalated repair, delegate a focused, read-only diagnosis
  to `diagnosis_model` returned by `retry` (Astra / high by default). Give it the
  failing evidence and relevant context, not the whole session. It returns a cause
  and proposed correction; the implementer applies the fix and required assessors
  verify it. For `direct-low`, switch to `delegated` before this diagnosed repair.
  Do not consult Astra routinely for low/standard tasks. Preserve stable problem
  IDs. Workers do not delegate, commit, switch branches or publish. Preserve
  unrelated user work.
- Architecture consultation is separate from escalated repair diagnosis. Do not
  start it automatically for high risk, uncertainty, a suggested plan or plan
  acceptance; require explicit user authorization covering that consultation.
- Save state at meaningful boundaries and before stopping. Keep full logs in the
  ignored task directory; handoffs contain outcomes, references and blockers.
  Report observed helper models/efforts, agent/repair counts and token usage only
  when exposed by the runtime; never infer usage from configured defaults.
- Helpers validate recorded artifacts, not whether a person approved, an agent was
  independent or a command actually ran. Record observed events honestly.
