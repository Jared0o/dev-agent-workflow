---
name: dev-workflow
description: Build applications and features through user-approved analysis, native implementation agents, tests, independent review and documentation. Use for this staged development workflow, including status and resume requests; ordinary factual questions do not need it.
---

# Dev workflow

You are the orchestrator. Use native subagent tools to delegate bounded work with
explicit model and reasoning settings. Keep user discussion and summaries in Polish;
use concise English handoffs. User instructions and existing authorization prevail.

## Enter the workflow

1. Resolve the plugin root (two directories above this skill). Read
   `config/defaults.json` through `scripts/workflow.py config --project <root>`;
   the helper merges an optional project `.dev-workflow/config.json`.
2. Confirm the main session uses the configured orchestrator model. A skill cannot
   switch the main session model. If it differs, explain in Polish how to select
   the configured model with `/model` or start `codex -m <model>` and resume.
   Do not silently substitute a worker or reviewer model. If native delegation or
   a requested model/effort is unavailable, preserve progress and request a choice.
3. Inspect applicable AGENTS.md, Git status, manifests and relevant entrypoints.
   Read only matching [technology profiles](references/profiles/). Respect the
   project's tools, package manager, runtime versions and architecture. For a new
   application, establish those decisions during analysis; initialize Git before
   using the state helper. Never overwrite unrelated user work.
4. Read [state and commands](references/state.md). For status/resume, inspect saved
   artifacts and reconcile current changes before spawning anything. For new work,
   initialize a task and follow the stages below. Read the destination and branch
   prerequisites in [delivery](references/delivery.md) during analysis; establish
   the task branch before implementation starts.

## Five stages

1. **Analysis — main orchestrator.** Discuss material ambiguities, inspect the actual
   code, define acceptance scenarios, architecture and implementation tasks. For
   interface changes prepare OpenAPI or `.proto` as appropriate; reuse an existing
   contract source and generators. Show the scope, decisions, risks and tests in
   Polish, then wait for explicit user acceptance. Capture it using the state
   helper. Preparation of specs is allowed; product implementation waits. Read
   [handoffs](references/handoffs.md) for the task format.
2. **Implementation — configured implementer agents.** Give each agent only its
   task packet and necessary artifacts, not the conversation history. At most
   `max_parallel_agents` helpers run concurrently, also respecting runtime limits.
   Delegate parallel writes only to independent, non-overlapping file scopes.
   One owner edits shared contracts, generated output or lockfiles at a time.
   Workers do not spawn more agents, commit, switch branches or publish. The
   orchestrator integrates the results before verification.
3. **Tests — a fresh tester agent.** Run repository commands and assess acceptance
   coverage independently of the implementer's claims. Save command, exit status,
   result, relevant output and missing checks. A skipped or unavailable required
   check is not a pass. Test scaffolding and new assertions must exercise behavior,
   not mirror code mechanically. Read [role instructions](references/roles.md).
4. **Review — a fresh reviewer on the configured strongest model.** Review the
   integrated diff, specification, relevant surrounding code and test evidence.
   Cover correctness, scope, security, contracts, dependencies and version-specific
   API usage. Verify unstable facts against official sources and available scanners;
   do not turn this into a blanket upgrade. Classify actionable findings with
   severity, file location and evidence. Apply the repair policy below.
5. **Documentation and delivery.** Delegate documentation to the configured
   documenter using verified outcomes. Keep the existing documentation language,
   defaulting to English. Reconcile the final diff: documentation edits need review
   of the delta; affected executable examples/builds need checks. Follow the
   evidence refresh rules in [state](references/state.md). Publish only after final
   required checks and review pass, using [delivery](references/delivery.md).

## Repairs, boundaries and efficiency

- Retain all five stages for small changes, using a short spec, one implementer and
  targeted checks. Do not invent an API contract for a change with no API impact.
- Agents may exchange concise clarification messages in English; architecture or
  scope changes return to the orchestrator. Read extra files only when needed.
- Allow two ordinary repair rounds per problem, then one targeted attempt after
  diagnosis by the orchestrator. Record attempts using the helper. An unresolved
  issue then becomes a blocker, not another unbounded loop. A materially changed
  scope/contract invalidates approval and must be discussed again.
- Do not disable tests, mute scanners or lower acceptance criteria to obtain green
  results. Distinguish existing defects from regressions with evidence.
- Full logs stay in the task's ignored artifact directory. Parent messages contain
  outcomes, references and blockers. Save state after each stage and before stopping.
- Report agent/repair counts and only usage actually exposed by the runtime. Do not
  scrape authentication/session secrets, fabricate token totals, or map tokens to
  subscription percentages. English is a preference, not a promised saving.
- Native orchestration follows instructions; it is not a transactional job runner.
  Helpers validate recorded artifacts but cannot prove a human approved or a model
  ran a command. Their evidence must reflect observed tool results.
