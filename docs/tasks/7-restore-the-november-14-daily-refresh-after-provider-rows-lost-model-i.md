Antti’s daily chart-data refresh stopped because Artificial Analysis removed model variant slugs from both leaderboard feeds. The prepared parser repair restores those identities from the public model catalog, keeps reasoning efforts separate, and preserves the previous output when a match is missing or ambiguous. The repair and freshly generated chart data are published on GitHub. Verification of the next automatic GitHub refresh remains open.

Owner: Codex in [the originating T3 thread]. Antti authorized publication and settlement when everything is done on 2026-11-14. No user action is needed now. A daily T3 check at 15:00 Europe/Helsinki is bound to that thread; its first run is 2026-11-15 13:00 UTC (15:00 Helsinki). Codex will inspect the next scheduled GitHub refresh, record completion and the conditional acceptance only after success, disable the check and request thread settlement. This task stays In Progress until that GitHub refresh succeeds. If no usable run appears by the November 17 check, stop the timer and give Antti the exact workflow UI steps.

## Verification on 2026-11-14

The new regression test first reproduced the failure: provider deduplication returned zero models instead of three distinct variants. After the repair, all 32 parser tests passed. They cover separate max/xhigh variants, deprecated models, host label suffixes, and preservation of the old output after unknown or ambiguous identity matches.

A live refresh then downloaded 1,165 provider rows and 741 model records. It produced 445 priced models with 395 estimated response times. The repository’s published data was not changed by this check. Its existing 65 unreviewed LiveBench identities remain excluded; this repair does not broaden benchmark identity matching.

```text
Ran 32 tests in 0.053s
OK
Deduplicated to 456 unique models
Models with pricing: 445
Models with response times: 395 (395 estimated)
```

The name-based provider joins also agreed with all 999 authoritative endpoint-to-model mappings available in the model index’s comparison payload. The other 166 provider rows had no performance measurements. Current release metadata still supplies family names, creators and release dates.

Ruff reports the same two pre-existing warnings before and after the change: a non-executable script with a shebang and use of timezone.utc. No new Ruff warnings were introduced. The project-local feed skill passes the skill validator and records the verified endpoints, identity rules and limitations.

Review the [parser repair], [regression tests] and [feed skill]. Saved evidence includes the [test output], [live refresh output] and [generated model data]. The original [failed GitHub job] remains historical evidence; the repaired workflow has not yet run on GitHub.

[parser repair]: ../../artificialanalysis.ai-parser.py?f
[regression tests]: ../../tests/test_parser.py?f
[feed skill]: ../../.agents/skills/artificial-analysis-feeds/SKILL.md?f
[test output]: http://tinni/.local/state/artificialanalysis-ai-parser/2026-11-14-refresh/aa-nov14-tests.log?f
[live refresh output]: http://tinni/.local/state/artificialanalysis-ai-parser/2026-11-14-refresh/aa-nov14-live-refresh.log?f
[generated model data]: http://tinni/.local/state/artificialanalysis-ai-parser/2026-11-14-refresh/aa-nov14-fixed-models.json?f
[failed GitHub job]: https://github.com/akaihola/artificialanalysis-ai-parser/actions/runs/43585184212/job/132418034382#step:5:1

## Publication on 2026-11-14

Repair commit `46dacfa` was pushed to GitHub master. A fresh live parser run then saved 445 priced models with 395 response-time estimates, and data commit `bd8214e` was also pushed to master. The published data does not depend on waiting for another scheduled refresh.

Starting the workflow manually failed with HTTP 403: the CLI credential was denied workflow dispatch, and the connected GitHub app was denied rerunning the original job. The collaborative browser’s Default profile showed Sign in. No credentials or workflow triggers were changed. These are access limits, not evidence that the repaired parser failed.

The T3 check is `scheduled-task:command:mcp:9946c97c-e511-4f46-a80f-4fda61f6f9a1:schedule-task:aa-refresh-verification-20261114-93bd7af3`. It is enabled, bound to this thread and reports its next run as `2026-11-15T13:00:00.000Z`. Its prompt has an explicit stop after success or the November 17 deadline. No worktree is attached to this thread, and the repair branch is preserved in Git and the scheduled check recreates its temporary checkout if needed, following the ephemeral-worktree rule. The main repository checkout has unrelated unpublished commits; they were preserved and not pushed.

[the originating T3 thread]: t3-thread://v1/93bd7af3-15f0-49ee-ad0e-e0f9c3fb4661

The [GitHub Pages deployment] for `bd8214e` succeeded. Fetching the [published model data] returned exactly the committed bytes: 445 models, including 395 with response-time estimates. The parser repair and updated chart data are live. Only independent verification of the next daily GitHub refresh remains. The temporary repair checkout can be removed after publication bookkeeping; its branch and immutable evidence are preserved.

[GitHub Pages deployment]: https://github.com/akaihola/artificialanalysis-ai-parser/actions/runs/43610221677
[published model data]: https://akaihola.github.io/artificialanalysis-ai-parser/models.json
