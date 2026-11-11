# Restore the daily model refresh

Antti and chart readers receive fresh model data and can filter slow models
again. The parser reads Artificial Analysis' complete public downloads and the
original LiveBench benchmark from its official archive. [The response-time
correction] restores marked 500-token estimates for the Max response time slider.

The refresh fix was merged on 2026-11-11 after Antti authorized publishing it,
and [the refresh run] passed. Antti then reported that Max response time no
longer changes the chart: all 94 chart-eligible current models have null timing
data. Passing the workflow did not establish that this feature still worked.
The correction was merged and published under the existing refresh-fix
authorization. [The corrected refresh run] and [the Pages deployment] passed.
The live chart now changes from 29 active variants to 24 at a 100-second limit,
with five faded dots; removing the limit restores all 29. No implementation or
deployment work remains. Owner: Antti for acceptance. Next action: open the
[chart at 100 seconds], check that lowering the limit changes the visible
variants, and reply `accept refresh repair` in the originating T3 discussion.
Codex then records acceptance; send any remaining correction in that discussion.

Failure: [daily refresh job], 2026-11-10.

## Verification on 2026-11-11

- PR #3 merged as `7bde95261d03544189abe520a741c5ec5f889cef`.
  GitHub ran all 29 parser tests, generated 393 estimates among 442 models,
  and pushed the refreshed data as `8eb5590`. The Pages deployment for that
  commit succeeded. Codex moved the actual published slider to a 100-second
  limit and back, confirming 29 to 24 active variants and five faded dots.
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
[chart at 100 seconds]: https://akaihola.github.io/artificialanalysis-ai-parser/intelligence-vs-cost.html?max_response_time=100
[the response-time correction]: https://github.com/akaihola/artificialanalysis-ai-parser/pull/3
[the corrected refresh run]: https://github.com/akaihola/artificialanalysis-ai-parser/actions/runs/42986576640
[the Pages deployment]: https://github.com/akaihola/artificialanalysis-ai-parser/actions/runs/42986609123
[the project acquisition skill]: ../../.agents/skills/artificial-analysis-data/SKILL.md
