Antti’s daily chart-data refresh failed because Artificial Analysis removed model variant slugs from its leaderboard feeds. The parser now restores canonical identities from the public model catalog while keeping reasoning efforts separate. The repaired automatic refresh and GitHub Pages deployment both succeeded on November 15, and the public chart data exactly matches the generated commit.

The work is complete. Antti authorized publication and settlement when everything was done on November 14; that condition is now satisfied. Codex records the conditional acceptance, stops the temporary verification timer and requests settlement of the originating conversation. The normal daily GitHub refresh remains enabled. Unrelated local commits in the main checkout were not pushed.

## Automatic verification on 2026-11-15

The [successful scheduled refresh] started at 10:52:30 UTC. Its logs show checkout of master at `49642df11e425e8bf562001ab3068ae625314f5d`, which contains parser repair `46dacfa`. GitHub ran all 32 parser tests, regenerated the data and pushed `6d3613c2761df8e1c23733beea9ffe2937c051a5` to master.

```text
Ran 32 tests in 0.073s
OK
Deduplicated to 456 unique models
SciCode scores for 253 models from the models leaderboard
Models with pricing: 445
Models with response times: 395 (395 estimated)
Saved 445 models to models.json (443,925 bytes)
[master 6d3613c] chore: update models.json
49642df..6d3613c  HEAD -> master
```

The [corresponding Pages deployment] started at 10:52:46 UTC and completed successfully at the generated commit. Codex fetched the [public model data] on November 15 and compared it with that commit’s file: the bytes match exactly, with SHA-256 `34db737ff70139def3154806bab39f5c299d5a4b0075ce49321c5a520e4a8416`. It contains 445 priced models and 395 response-time estimates. The [live chart] uses this data.

## Repair and earlier checks

The [parser repair] obtains canonical model slugs from the public model catalog. Model scores join by model ID; provider rows match the longest complete canonical name within the exact release and reasoning effort. Missing or ambiguous matches stop the refresh and preserve the old output.

The [regression tests] first reproduced the failure, returning zero models instead of three variants. They now cover separate max/xhigh variants, deprecated models, host-label suffixes and preservation of the previous output after unknown or ambiguous matches. The [November 14 fixture] retains the relevant real feed fields. Live name matches also agreed with all 999 authoritative endpoint-to-model mappings available for comparison; the other 166 endpoints had no performance measurements.

Repair commit `46dacfa` and manually generated data commit `bd8214e` were published on November 14. Manual workflow dispatch and job rerun were denied with HTTP 403, so the verification waited for the existing daily schedule. No credentials or workflow triggers were changed. That access limit did not prevent the automatic refresh verified above.

The [feed maintenance skill] records the verified endpoints, identity rules and access limits. Ruff reports the same two pre-existing warnings before and after the repair: a non-executable script with a shebang and use of timezone.utc. The existing 65 unreviewed LiveBench identities remain excluded; this repair does not broaden benchmark identity matching.

## Closeout

The temporary T3 verification timer is disabled after successful verification. Completion and conditional acceptance are published in the task tracker before settlement. The independent verification checkout is removed after cleanliness and publication checks; its branch is preserved. No main checkout or unrelated worktree is removed.

[successful scheduled refresh]: https://github.com/akaihola/artificialanalysis-ai-parser/actions/runs/43706171470
[corresponding Pages deployment]: https://github.com/akaihola/artificialanalysis-ai-parser/actions/runs/43706190521
[public model data]: https://akaihola.github.io/artificialanalysis-ai-parser/models.json
[live chart]: https://akaihola.github.io/artificialanalysis-ai-parser/intelligence-vs-cost.html
[parser repair]: ../../artificialanalysis.ai-parser.py
[regression tests]: ../../tests/test_parser.py
[November 14 fixture]: ../../tests/fixtures/aa-leaderboards-2026-11-14.json
[feed maintenance skill]: ../../.agents/skills/artificial-analysis-feeds/SKILL.md
