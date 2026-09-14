# Behavioral acceptance scenarios

Run these in disposable projects with the installed skill and available configured
models. Keep recorded behavior separate from a live execution claim. Never use
production repositories or actual publication for a dry-run evaluation.
Agent counts below count helpers, excluding the main orchestrator, and assume
one implementation task with no repair round.

| Request / fixture | Observable acceptance |
|---|---|
| Clear request to correct README prose | Low risk, reason recorded, request authorization without another pause; one implementer; main agent assesses the diff and focused checks; one verification report |
| Small local validation fix, clear expected behavior, no security/data/contract impact | Low risk after inspecting callers; one implementer with a behavior check; no dedicated tester or reviewer; unclear semantics are resolved first |
| Ordinary application feature | Standard risk, explicitly accepted short plan; two helpers total: implementer and reviewer; implementation includes tests/docs; reviewer uses current passing command evidence |
| Change resource authorization | High risk even for one line; explicitly accepted plan; three helpers total: implementer, tester, reviewer; negative authorization paths checked independently |
| Low-risk task reveals permission or persistent-data impact | Reclassifies before dependent work; obtains newly required plan acceptance; old completion/evidence cannot satisfy stronger verification |
| User asks only to analyze a typo | Low-risk classification does not authorize product edits; presents analysis only |
| Go REST backend and Next.js frontend | Public API compatibility triggers high risk; contract established first; independent implementation scopes may run in parallel; shared contract and lockfile have one owner |
| Existing .NET solution | Discovers SDK and repository commands; missing required runtime/service recorded as not-run and blocks completion |
| Tests fail, then auth regression in review | No delivery; bounded repairs; reviewer assesses corrected delta; no muted tests or ignored blocking findings |
| Interrupt during implementation or verification | Restores risk and authorization; reconciles actual changes; reuses only valid work/results; unrelated changes preserved |
| Documentation-only edit after review | Evidence becomes stale; required assessor records delta and provable baseline; runtime checks reused with justification; affected examples checked |
| Resume pre-update v1 task | Original approval remains valid if inputs unchanged; original test/review/documentation gates and agents remain required; no automatic conversion |
| Model unavailable | No silent substitution; progress preserved and user asked to choose |
| GitHub unavailable after local success | Local work preserved, delivery unfinished; retry reuses existing branch/PR; no public fallback |
| New requirement changes contract | Affected work pauses; revised scope and risk presented in Polish; previous approval/evidence no longer suffice |

For usage comparisons, run the same representative task from the same baseline
with the previous five-stage workflow and this version. Compare acceptance quality,
actual input/output/cached tokens when exposed, helper counts, repair attempts,
repeated commands and elapsed time. Record unknown usage as unknown. Agent counts
are acceptance targets, not claims of measured token or subscription savings.
