# Existing v1 tasks

Use this only when `status` reports `schema_version: 1`. Do not convert the task
or relax its gates. New tasks use v2. Configuration retains its v1 shape and model
roles so the update alone does not invalidate an existing approval digest.

The original sequence remains `analysis → implementation → tests → review →
documentation → delivery → done`. All five work stages remain required even for
small changes, with concise specifications and targeted checks.

1. Analysis: prepare spec/tasks and obtain explicit user acceptance. Record with
   `approve --confirmed-by-user`; request-based authorization is not supported.
2. Implementation: configured implementer agents own bounded tasks and focused
   checks. Orchestrator integrates their changes and records `task-done`.
3. Tests: a fresh configured tester independently runs relevant repository checks
   and evaluates acceptance coverage. Missing required checks are `not-run`.
4. Review: a fresh configured reviewer reviews the integrated code, specification
   and test evidence. Blocking findings require bounded repairs and delta review.
5. Documentation: configured documenter updates docs from verified outcomes.
   Reconcile changed files with the tester and independent reviewer before delivery.

Use distinct nonempty reports with `record --kind tests|review|documentation
--result pass|fail|not-run --report <path> --fingerprint <before-checks>`.
Tests gate leaving `tests`; tests and review gate leaving `review`; all three
gate leaving `documentation` and completing `delivery`. All reports must match the
current fingerprint and their recorded content hashes.

Any project edit makes evidence stale. Rerun affected checks and inspect the changed
review surface. For documentation deltas, the tester may retain runtime results
with a recorded justification and provable baseline; run affected example/doc
checks. The independent reviewer performs the equivalent delta assessment. Without
a reconstructible baseline, rerun required checks and review. Never re-stamp old
reports without assessing the delta.

The shared [state rules](state.md), [handoffs](handoffs.md), configured repair
limits and [delivery requirements](delivery.md) otherwise apply. Legacy evidence
kinds are not accepted on v2 tasks, and v2 verification reports do not satisfy v1.
