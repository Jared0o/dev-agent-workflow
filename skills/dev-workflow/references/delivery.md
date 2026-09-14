# Delivery

Default completion is a branch plus draft PR in the existing GitHub repository.
Before analysis ends, inspect the remote and base branch and record the intended
destination. If there is no repository, create a private one using `gh repo create
--private` once the project name/destination is established. Never change an
existing repository's visibility; a branch has the repository's visibility.

The orchestrator owns Git operations. Begin from a task branch before parallel
writes. If unrelated changes exist, use a separate worktree from the agreed base
or preserve them with an explicit file ownership list; never auto-stash/reset them.
Only stage the reviewed task files. Exclude `.dev-workflow/`, secrets and logs.
Use `git diff --cached` to confirm what will be committed, and inspect untracked
files too. Commit after required tests, independent review and documentation pass.

Check `gh auth status`. Push the task branch normally (no force push), then inspect
whether a PR for this exact head/base already exists before `gh pr create --draft`.
Reuse that PR on resume. Write the body to a temporary file and use `--body-file`;
do not interpolate multiline model text into shell commands. The body leads with
the concrete problem/result, then relevant validation and limitations. Do not add
reviewers or send comments/messages unless separately requested.

Save commit SHA, branch, base and PR URL to `delivery.json` in the task directory;
advance to `done` only after confirming the PR exists. Publication failure leaves
the task in delivery with its local work and evidence intact. Never fall back to
a public repository. Merge, auto-merge and deployment need separate user direction.

Final Polish reply: outcome, key changes, tests actually run, limitations, draft PR
link and observed usage (when available). A stopped task reports the blocker and
the command to resume, without claiming completion.
