# Go

Load for a task that changes Go code or its public interfaces.

## Discover before planning

- Read `go.mod`, any `go.work`, CI configuration, and repository task scripts. Record the declared toolchain, relevant modules, and actual build/test commands in the task packet. Preserve the existing framework and module layout.
- Identify the affected package and its callers, existing test helpers, and how local services or test databases are started. Do not assume that running from the repository root covers every module.
- For a new service, agree on the transport and required dependencies during analysis; do not introduce a framework merely to match this profile.

## Implementation and contracts

- Follow the project's handling of context cancellation, timeouts, errors, configuration, and dependency injection. Keep shared module and dependency-file changes under one owner's control.
- For an affected REST boundary, use the repository's OpenAPI source and generation process; for gRPC, use its `.proto` source and generators. Establish request, response, error, and compatibility expectations before parallel client/server work. Preserve another established contract approach when present.
- Review authorization at the resource boundary, input and payload limits, unsafe query construction, secret handling, and cancellation around external calls where relevant to the change.

## Verification

- Prefer the existing commands. Without wrappers, consider scoped `go test`, `go vet`, and a formatting check for changed packages; select flags using the installed toolchain and repository conventions.
- Add behavior-focused tests for acceptance criteria and affected error paths. Use race checks when concurrent behavior changes and the environment supports them. Run integration tests when changed behavior depends on a service, database, or generated contract.
- Reuse configured vulnerability checks. Report missing tooling or unavailable services as an unperformed check, with the affected claim; do not install a new toolchain or audit tool silently.
