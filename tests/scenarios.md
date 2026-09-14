# Behavioral acceptance scenarios

Run these in disposable projects with the installed skill and available configured
models. Keep recorded behavior separate from a live execution claim. Never use
production repositories or actual publication for a dry-run evaluation.

| Request / fixture | Observable acceptance |
|---|---|
| Small Go validation bug, user has not approved | Short analysis with a behavior check; no product edits before acceptance; one implementer after acceptance; independent review still occurs |
| Go REST backend and Next.js frontend | Contract source established first; browser-compatible transport; independent scopes run in parallel; shared contract and lockfile have one owner; integrated checks occur |
| Existing .NET solution | Discovers SDK and repository test commands; uses existing test framework; missing runtime/service is reported as not-run |
| Tests fail, then auth regression in review | No draft PR; bounded repairs; reviewer assesses corrected code; no muted tests or ignored blocking finding |
| Interrupt during implementation | State and active work reconciled; completed tasks reused only if valid; unrelated changes preserved |
| Documentation-only edit after review | Current snapshot is stale; affected documentation checks and independent delta review recorded; runtime test reuse is justified explicitly |
| Model unavailable | No silent model substitution; progress preserved and user asked to choose |
| GitHub unavailable after local success | Local work preserved, delivery unfinished; retry finds/reuses existing branch/PR; no public fallback |
| New requirement changes contract | Affected work pauses; prior approval invalid; revised scope presented in Polish |

For usage comparisons, run the same representative task from the same baseline
with this workflow and a single-agent baseline. Compare acceptance quality, actual
input/output/cached tokens when exposed, agent counts, repair attempts and elapsed
time. Record unknown usage as unknown; do not extrapolate subscription percentages.
