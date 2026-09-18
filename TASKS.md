# Issue tracking for artificialanalysis.ai parser

Rules for TASKS.md usage are at the bottom of the file.

## Ordered backlog

## Scheduled

## In progress

- [*] The empty chart and table for Terminal-Bench v4.0 come from a renamed upstream
  field. The live [models feed](https://artificialanalysis.ai/leaderboards/models) now
  uses `terminalBench40`;
  [our parser](https://gogo.crane-boa.ts.net:8449/home/agent/.kandev/tasks/why-is-the-terminal_b99btn94/artificialanalysis-ai-parser/artificialanalysis.ai-parser.py:124)
  expects `terminalbenchV40`. Consequently, all 410 models have
  `terminalbench_v4_0: null`, and both views exclude them. The refresh validation only
  checks SciCode, so this failure passes unnoticed. Fix the parser.

## Completed

- [*] Add Terminal-Bench v4.0 as a selectable benchmark

- [*] Restore the Coding Pareto graph and table with SciCode

- [*] Move the Full screen button to the chart top-right, include filters in
  full-screen mode, and use the full window height

- [*] Adjust max response time using horizontal scrolling on a touchpad

- [*] In a GitHub workflow, regenerate `models.json` daily and commit any
  changes to `master`

- [*] Add Pareto chart Y-axis zoom

[*]: TASKS.md

---

## Rules

Here are the rules for TASKS.md usage:

### Unverified proposals

- Bullets under `## Unverified proposals` are ideas that nobody has reviewed yet. They
  are not candidates for scheduling: a heartbeat never picks from this section. Antti
  reviews a proposal and moves it into `## Ordered backlog`, or deletes it.
- Before adding a proposal, read the whole section. Drop an exact duplicate. Merge a
  similar existing proposal with the new one into a single revision that combines the
  ideas of both.

### Invariant: one heading per issue

At any time, each issue's bullet must be under exactly one `##` heading (for example
`## Ordered backlog` or `## In progress`). It must never be under two headings at the
same time.

- Before you commit any change to TASKS.md, read the whole file and check that no bullet
  appears under two headings.

### TASKS.md maintenance sessions

- Each backlog item must be prefixed with either
  - a numbered reference-style link (e.g. `[1]`) to a description file, or
  - `[*]` to indicate no description file is needed for a simple task.
- Link references are listed between `## Completed` and `## Rules`.
- If any issue is missing a link:
  - Create the first missing numbered description file in
    docs/tasks/<N-issue-description>.md and add the link
- Any completed tasks which haven't yet been moved from `## In Progress` to
  `## Completed` should be moved there.
- Any in progress tasks which haven't yet been moved from `## Ordered backlog` or
  `## Scheduled` to `## In Progress` should be moved there.
- Remove all issues the user has moved to the `## Accepted` section along with any
  related description files in `docs/tasks/` and the reference-style links pointing to
  them.
- Ensure there are no duplicate sections, and that they are in the correct order:
  `## Unverified proposals` -> `## Ordered backlog` -> `## Scheduled` ->
  `## In Progress` -> `## Completed` -> `## Accepted` -> `## Rules`.

### Modifying issues

- Ensure dependencies between issues are correctly updated.
- State dependencies using
  - indented `- Depends on: [N]` bullets in TASKS.md, and
  - YAML frontmatter in description files.
- Ensure backlog order respects dependencies.
- When you move an issue to a different section, move its lines without a change. Keep
  the prefix, the bullet text and the line wrapping the same. Git can then see the move,
  and concurrent moves do not cause a conflict.

### Workflow for new issue completion

1. Choose issue and schedule work (typically by a heartbeat)

- Pick the first backlog issue with no dependency to any uncompleted issue.
- Move it under `## Scheduled` in `TASKS.md` and remove it from `## Ordered backlog` in
  the `main` branch and commit.

2. Work on the issue (typically by a task workflow)

- Rebase the worktree feature branch on `main` before moving the issue, and keep it
  rebased afterwards.
- Move the issue under `## In progress` in `TASKS.md` in the worktree branch, ensure
  it's not in `## Ordered backlog`, and commit.
- Create or update, review and refine a plan in docs/tasks/<N-issue-description>.md in
  `main` if more description is needed than nicely fits in a bullet point. If you
  created a plan document, link to it using a new `[N]` reference-style link.
- Commit the description file (if any) in `main`.
- Implement the plan, and lint, test, review and refine the implementation in the
  worktree feature branch.

3. Merge and deploy (typically by last steps of a task workflow)

- Merge the rebased branch on `main`, and remove the worktree and branch.
- Move the issue from `## In progress` to `## Completed` in TASKS.md and commit.
- Do any deployment steps if defined in the general development worklow.

When TASKS.md conflicts during a rebase or merge:

- Use `main`'s version of every section as the base.
- Apply again only the move of your own issue.
- Never restore, add again or re-word another issue's bullet from your side of the
  conflict.
- After resolving the conflict, read the whole file and ensure that each bullet is under
  exactly one `##` heading.
