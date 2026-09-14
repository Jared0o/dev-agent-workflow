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
   repair and delivery settings. The main session must use the configured
   orchestrator model; the skill cannot switch it. If a requested model/effort or
   native delegation is unavailable, preserve progress and request a replacement
   choice rather than silently substituting.
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

## Choose the required verification

| Risk | Criteria | Helpers for one implementation task |
|---|---|---|
| `low` | Plain documentation, cosmetic UI, or an unambiguous local fix with no security, persistent-data or contract impact | One implementer; orchestrator checks the result |
| `standard` | Other understood work without high-risk triggers; the default | One implementer and one independent reviewer |
| `high` | Authentication, authorization, payments, migrations, destructive operations or public API compatibility | One implementer, independent tester and independent reviewer |

Inspect uncertain impact before classifying; file count is not a risk measure.
A clear user request authorizes low-risk work without another approval pause.
Record request authorization explicitly; selecting `low` alone is not approval.
For standard/high work, present the plan and wait for explicit acceptance unless
the user already accepted that exact plan. A request to only analyze never
authorizes implementation, even at low risk.

## Execute

1. **Implementation, tests and documentation.** Delegate to one configured
   implementer by default. The same agent runs focused required checks and updates
   relevant documentation before verification; do not spawn a documenter for v2.
   Parallelize only independent scopes within `max_parallel_agents` and runtime
   limits. Shared contracts, generated files and lockfiles have one owner.
2. **Verification.** Integrate changes and use observed check results for the current
   code. At low risk, inspect the diff and evidence yourself. At standard risk,
   use a fresh configured reviewer. At high risk, first use a fresh tester for
   acceptance coverage and affected integrations, then a distinct reviewer.
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
- If new information increases risk, update the classification and required
  verification. Pause dependent work for any newly required user acceptance or
  material scope/contract change. Reapproval is for an accepted plan revision,
  never a way to reset a failing task's repair budget.
- Use configured repair limits (two ordinary rounds and one diagnosed attempt by
  default). Preserve stable problem IDs. Workers do not delegate, commit, switch
  branches or publish. Preserve unrelated user work.
- Save state at meaningful boundaries and before stopping. Keep full logs in the
  ignored task directory; handoffs contain outcomes, references and blockers.
  Report agent/repair counts and token usage only when exposed by the runtime.
- Helpers validate recorded artifacts, not whether a person approved, an agent was
  independent or a command actually ran. Record observed events honestly.
