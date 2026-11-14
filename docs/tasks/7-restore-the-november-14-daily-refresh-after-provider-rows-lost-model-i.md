Antti’s daily chart-data refresh stopped because Artificial Analysis removed model variant slugs from both leaderboard feeds. The prepared parser repair restores those identities from the public model catalog, keeps reasoning efforts separate, and preserves the previous output when a match is missing or ambiguous. The fix is verified locally and is not published.

Owner: Codex in the originating T3 thread. Antti’s next action is to authorize publication there. After approval, Codex will push the prepared repair to master, run the daily refresh workflow, inspect its result and report in the same thread. No automatic continuation is registered. This task stays In Progress until the GitHub refresh succeeds.

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
