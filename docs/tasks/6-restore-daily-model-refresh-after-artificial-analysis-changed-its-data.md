# Restore the daily model refresh

Antti and chart readers receive fresh model data again with [the merged fix].
The parser now reads Artificial Analysis' complete public downloads, including
deprecated models, and the original LiveBench benchmark from its official archive.
The previous daily refresh stopped at `rows not found in response`.

The refresh fix was merged on 2026-11-11 after Antti authorized publishing it,
and [the refresh run] passed. Antti then reported that Max response time no
longer changes the chart: all 94 chart-eligible current models have null timing
data. Passing the workflow did not establish that this feature still worked.
The task is reopened. The prepared correction restores a clearly marked
500-token estimate from current first-answer latency and output speed. Owner:
Codex in the originating T3 discussion. Next action: publish the correction,
run the updated GitHub workflow, and verify the slider on the published [chart].

Failure: [daily refresh job], 2026-11-10.

## Verification on 2026-11-11

- The response-time correction passed 29 parser tests and eight Chromium/Firefox
  checks. The refreshed dataset has 393 marked estimates, including 92 of the
  94 current models with an Intelligence score and positive task cost. New
  browser checks load the actual dataset, lower the slider to 100 seconds,
  verify that slow models fade and leave the table, and restore No limit.
- A regression test against the previous parser demonstrated that it accepted
  refreshes with no usable current chart timings. The corrected parser rejects
  those refreshes before replacing the existing dataset.
- PR #2 merged as `c8dfb046d05cf3ba5f1b74c835268c35de5418eb`.
  Codex dispatched [the refresh run] against this commit. GitHub
  installed the dependency, passed all 24 parser tests, downloaded the full
  provider and model data, and saved 442 priced models. The workflow pushed
  its data update to master as `f5bb827`.
- Direct downloads from the published chart confirmed 442 models, the new
  LiveBench archive provenance, and the updated sparse-result recovery controls.
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
response-time measurement. The correction estimates a 500-token answer using
model-level time to first answer token plus 500 divided by output tokens per
second, including reasoning time. Estimates are marked `≈`; their source
aggregates differ from the old reported median. Unknown first-answer latency
stays unknown. Task execution time measures something else and is not used.

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
[the merged fix]: https://github.com/akaihola/artificialanalysis-ai-parser/pull/2
[the refresh run]: https://github.com/akaihola/artificialanalysis-ai-parser/actions/runs/42975990794
[chart]: https://akaihola.github.io/artificialanalysis-ai-parser/intelligence-vs-cost.html
[the project acquisition skill]: ../../.agents/skills/artificial-analysis-data/SKILL.md
