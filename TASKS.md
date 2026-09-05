# Issue tracking for artificialanalysis.ai parser

Rules for TASKS.md usage are at the bottom of the file.

## Ordered backlog

- Move `Full screen` button to the top right corner of the chart and use the
  diagonal two-head arrow symbol instead of a text label for it. Include the
  filters panel in the full screen view of the chart. Utilize the full height of
  the window in full screen mode.

- Adjust max response time using horizontal scrolling on a touchpad.

- Add a toggle for zooming the chart vertically to only include the Y range of
  points on the Pareto line.

## In progress

- [*] Add Pareto chart Y-axis zoom
- [*] Adjust max response time using horizontal scrolling on a touchpad
- [*] In a GitHub workflow, regenerate `models.json` daily
  and commit any changes to `master`

## Completed

[*]: TASKS.md

---

## Rules

Here are the rules for TASKS.md usage:

### TASKS.md maintenance sessions

- Each backlog item must be prefixed with either
  - a numbered reference-style link (e.g. `[1]`) to a description file, or
  - `[*]` to indicate no description file is needed for a simple task.
- Link references are listed between `## Completed` and `## Rules`.
- If any issue is missing a link:
  - Create the first missing numbered description file in
    docs/tasks/<N-issue-description>.md and add the link

### Modifying issues

- Ensure dependencies between issues are correctly updated.
- State dependencies using
  - indented `- Depends on: [N]` bullets in TASKS.md, and
  - YAML frontmatter in description files.
- Ensure backlog order respects dependencies.

### Workflow for new issue completion

1. Choose issue and schedule work (typically by a heartbeat)
- Pick the first backlog issue with no dependency to any uncompleted issue.
- Move it under `## Scheduled` in `TASKS.md` and remove it from `## Ordered
  backlog` in the `main` branch and commit.

2. Work on the issue (typically by a task workflow)
- Move the issue under `## In progress` in `TASKS.md` in the worktree branch,
  ensure it's not in `## Ordered backlog`, and commit.
- Create or update, review and refine a plan in
  docs/tasks/<N-issue-description>.md in `main` if more description is needed
  than nicely fits in a bullet point. If you created a plan document, link to it
  using a new `[N]` reference-style link.
- Commit description file (if any) and TASKS.md in `main`.
- From now on, ensure worktree feature branch is always rebased on `main`.
- Implement the plan, and lint, test, review and refine the implementation in
  the worktree feature branch.

3. Merge and deploy (typically by last steps of a task workflow)
- Merge the rebased branch on `main`, and remove the worktree and branch.
- Move the issue from `## In progress` to `## Completed` in TASKS.md and commit.
- Do any deployment steps if defined in the general development worklow.
