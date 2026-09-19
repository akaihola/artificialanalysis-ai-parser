# Fix Terminal-Bench v4.0 field parsing

This report describes the failure before the fix, not the current feed or parser.
The field fix landed in `e912f4b`; `2920aba` restored the checked-in scores.
This is separate from adding Terminal-Bench as a selectable benchmark.

The empty chart and table for Terminal-Bench v4.0 come from a renamed upstream
field. The live [models feed](https://artificialanalysis.ai/leaderboards/models) now
uses `terminalBench40`;
[our parser](https://github.com/akaihola/artificialanalysis-ai-parser/blob/a28f0a6ea6a514e62adb7376313270a7096bdfd8/artificialanalysis.ai-parser.py#L122)
expects `terminalbenchV40`. Consequently, all 410 models have
`terminalbench_v4_0: null`, and both views exclude them. The refresh validation only
checks SciCode, so this failure passes unnoticed. Fix the parser.
