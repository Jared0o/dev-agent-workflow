# React / Next.js

Load for a task that changes a React frontend; apply Next.js details only when that framework is present.

## Discover before planning

- Inspect package manifests, the lockfile, runtime-version configuration, workspace layout, CI, and scripts. Record the package manager, framework versions, relevant workspace, and existing build, type-check, lint, and test commands in the task packet.
- Identify the router, rendering approach, design system, state/data libraries, and test tools. Preserve those choices. Do not assume framework commands from memory: use project scripts and installed command help.
- For a new frontend, establish its framework and runtime during analysis without adding libraries beyond the approved need.

## Implementation and contracts

- Follow existing component, styling, and accessibility conventions. Include loading, empty, error, and successful states that belong to the accepted behavior.
- Locate the existing API contract and client-generation process. For REST, use the agreed OpenAPI source; for a gRPC-backed system, confirm the actual browser-facing adapter or gateway and its contract instead of assuming direct browser access to the backend transport.
- For Next.js, inspect the installed version and existing server/client boundaries before using framework APIs. Keep secrets and privileged actions on the appropriate server side; verify authorization for every changed server entry point.
- Review untrusted HTML, input handling, cookie/session use, and cache behavior where affected. Give shared manifests, lockfiles, routing configuration, and contracts a single owner during parallel work.

## Verification

- Run the repository's relevant type, lint, test, and build checks. Reuse its browser or component tests for changed user flows; verify keyboard access and visible error behavior when UI interaction changes.
- Check the agreed client/server contract after integration. Use existing dependency-audit tooling where available and distinguish findings from tooling or network failures.
- Report missing runtime versions, browser dependencies, or backend services as unperformed checks. Do not replace the package manager, regenerate a lockfile incidentally, or install a new testing framework to satisfy this profile.
