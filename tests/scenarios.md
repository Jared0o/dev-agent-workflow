# Behavioral acceptance scenarios

Run these in disposable projects with the installed skill and available configured
models. Keep recorded behavior separate from a live execution claim. Never use
production repositories or actual publication for a dry-run evaluation.
Agent counts below count helpers, excluding the main orchestrator, and assume
one implementation task with no repair round.

| Request / fixture | Observable acceptance |
|---|---|
| Clear request to correct README prose | Low risk, direct-low mode and reason recorded, request authorization without another pause; zero helpers; main agent implements and assesses the diff and focused checks; one verification report |
| Replace displayed "Sign in" with "Log in" | Inspects context to confirm label-only change; direct-low; zero helpers; main runtime ID is both sole implementer and orchestrator assessor; required checks pass |
| Main session uses a user-selected model/effort | Keeps that model and effort without a replacement prompt; configured Sol / medium is only a recommendation; helpers use explicit effective models |
| Two ordinary repairs fail on one stable problem | Third retry returns configured Astra / high diagnosis model; one read-only diagnosis helper; worker applies correction; risk-required assessments remain; fourth retry blocked with default limits |
| Direct task needs an escalated repair | Switches to delegated with a fresh execution reason, preserves attempts, obtains applicable authorization and sends diagnosis to configured model; worker repairs; all implementer IDs retained; if main contributed edits, a fresh configured reviewer performs the low orchestrator assessment |
| Resume old v2 state without execution fields | Remains delegated; original digest shape preserved; low self-assessment rejected; changed effective config invalidates approval |
| Small local validation fix, clear expected behavior, no security/data/contract impact | Low risk after inspecting callers; one implementer with a behavior check; no dedicated tester or reviewer; unclear semantics are resolved first |
| Ordinary application feature | Standard risk, explicitly accepted short plan; two helpers total: Terra / medium implementer and Sol / medium reviewer; implementation includes tests/docs; reviewer uses current passing command evidence |
| Change resource authorization | High risk even for one line; explicitly accepted plan; three helpers total: Terra / medium implementer and tester, Astra / high reviewer; negative authorization paths checked independently |
| Low-risk task reveals permission or persistent-data impact | Reclassifies before dependent work; obtains newly required plan acceptance; old completion/evidence cannot satisfy stronger verification |
| User asks only to analyze a typo | Low-risk classification does not authorize product edits; presents analysis only |
| Go REST backend and Next.js frontend | Public API compatibility triggers high risk; contract established first; independent implementation scopes may run in parallel; shared contract and lockfile have one owner |
| Existing .NET solution | Discovers SDK and repository commands; missing required runtime/service recorded as not-run and blocks completion |
| Tests fail, then auth regression in review | No delivery; bounded repairs; reviewer assesses corrected delta; no muted tests or ignored blocking findings |
| Interrupt during implementation or verification | Restores risk, execution mode and authorization; reconciles actual changes; reuses only valid work/results; unrelated changes preserved |
| Documentation-only edit after review | Evidence becomes stale; required assessor records delta and provable baseline; runtime checks reused with justification; affected examples checked |
| Resume pre-update v1 task | Original approval remains valid if inputs unchanged; original test/review/documentation gates and agents remain required; no automatic conversion |
| Model unavailable | No silent substitution; progress preserved and user asked to choose |
| GitHub unavailable after local success | Local work preserved, delivery unfinished; retry reuses existing branch/PR; no public fallback |
| New requirement changes contract | Affected work pauses; revised scope and risk presented in Polish; previous approval/evidence no longer suffice |

For usage comparisons, run the same representative task from the same baseline
with the previous workflow and this version, using the same main model/effort
for the delegation comparison. Measure model/effort changes separately. Compare acceptance quality,
actual input/output/cached tokens when exposed, helper counts, repair attempts,
repeated commands and elapsed time. Record unknown usage as unknown. Agent counts
are acceptance targets, not claims of measured token or subscription savings.
