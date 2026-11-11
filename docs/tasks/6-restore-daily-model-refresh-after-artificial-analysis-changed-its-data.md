# Restore the daily model refresh

Antti and chart readers can receive fresh model data again with the prepared fix.
The parser now reads Artificial Analysis' complete public downloads, including
deprecated models, and the original LiveBench benchmark from its official archive.
The previous daily refresh stopped at `rows not found in response`.

Owner: Antti for the publishing decision in this T3 thread; Codex for merging
and running GitHub Actions after authorization. Next action: review the fix and
the source limitations below, then authorize merging the pull request. The task
stays In Progress until the updated workflow succeeds on GitHub.

Failure: [daily refresh job], 2026-11-10.

## Verification on 2026-11-11

- The original refresh command failed locally with the same missing `rows` error.
  The repaired refresh downloaded 1,169 provider rows and 734 complete models,
  then saved 442 priced models, including 272 deprecated models.
- All 24 parser tests passed, including malformed full-download cases that
  preserve the previous output. The updated GitHub workflow installs the pinned
  dependency and runs these tests before refreshing data.
- Eight browser checks passed across Chromium and Firefox: real-data smoke
  tests and recovery from reasoning/deprecation filters, including sparse
  current results with additional deprecated model families.
- Type checks passed. Ruff reports only the parser's pre-existing nonexecutable
  shebang and UTC-alias suggestions; checking with those excluded passed.
- Verified service formats and a tested local browser-check helper are recorded
  in [the project acquisition skill].

## Source limitations

The full Artificial Analysis feeds no longer contain the former end-to-end
response-time measurement. The refreshed data leaves it null, so the chart's
time filter includes those models. Task execution time measures something else
and is not used as a substitute.

Only two models have both an AIME 2025 score and a positive task cost. Math's
chart needs three points and shows its insufficient-data explanation; individual
results remain available in the table. LiveBench can recover enough points by
offering deprecated model families when current results are too sparse.

LiveBench's former GitHub source returns 404. The official v1 archive retains
all six reviewed model IDs. Downloads record file hashes and retrieval time;
they no longer have a public Git commit identifying an atomic upstream revision.

Acceptance: the same refresh command succeeds with live data, parser tests pass,
and existing benchmark meanings and output-preservation checks remain intact.

[daily refresh job]: https://github.com/akaihola/artificialanalysis-ai-parser/actions/runs/42805407520/job/129793147490
[the project acquisition skill]: ../../.agents/skills/artificial-analysis-data/SKILL.md
