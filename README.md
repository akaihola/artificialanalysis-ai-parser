# artificialanalysis-ai-parser

This fork adopts only the Artificial Analysis data parsing from upstream and repurposes the repository for an interactive [intelligence-vs-cost visualization](https://akaihola.github.io/artificialanalysis-ai-parser/intelligence-vs-cost.html).

Parser for [artificialanalysis.ai](https://artificialanalysis.ai) — extracts AI model data (pricing, benchmarks, speed) **without an API key**.

## Why?

The idea started from [demianarc/artificialanalysisscrapper](https://github.com/demianarc/artificialanalysisscrapper) — a Python scraper that fetched model data from the Artificial Analysis Next.js RSC endpoint. It was a clever approach: the site's React Server Components stream exposed the full dataset (`hostsModels`) in a single 10 MB response, no authentication needed.

However, after the site's redesign ("A new look for Artificial Analysis"), the old line-based parser broke completely. The RSC format changed from simple `key:value` pairs to a chunk-referenced wire format with `I[...]` inline references and `$c:props:...` circular links.

In August 2026 the site changed its data model again. The `hostsModels` key is gone. The data now lives in a `rows` array with camelCase field names. The new data also contains two useful metrics: the cost to run one benchmark task, and the median end-to-end response time.

The Python parser in this project:

- **Extracts** the `rows` array from the RSC stream with a standard JSON decoder
- **Deduplicates** ~1,100 host-model pairs down to ~400 unique models. For each model, it prefers the endpoint of the model creator. If there is none, it takes the complete endpoint with the lowest cost per task
- **Cleans** the output to only essential fields (pricing, IQ, speed, cost per task, response time, context window)
- **Outputs** `models.json` — ~390 models with pricing, ready for downstream use

The result is a self-contained Python script with zero dependencies beyond the standard library.

## Quick start

### Python

```bash
python3 artificialanalysis.ai-parser.py --minimal --pretty
```

### Output

```
Downloading RSC data from https://artificialanalysis.ai/leaderboards/providers?_rsc=hgvan ...
Downloaded 2,496,605 bytes
Extracted 1105 raw entries (host-model pairs)
Deduplicated to 411 unique models
Models with pricing: 388

Saved 388 models to models.json (240,799 bytes)

Top model: Claude Opus 5 (max) (Anthropic)
  IQ: 63.05 | Coding: None | Math: None
  Price: $5.00 in / $25.00 out
  Speed: 59 tok/s
```

## models.json structure

Each entry:

| Field | Description |
|---|---|
| `name` | Model name |
| `creator` | AI lab / company |
| `provider` | The API host that the numbers come from |
| `slug` | URL-friendly identifier |
| `intelligence_index` | AA Intelligence Index score |
| `coding_index` | SciCode score scaled to 0–100, joined from the models leaderboard |
| `terminalbench_v4_0` | Terminal-Bench v4.0 score scaled to 0–100, joined from the models leaderboard; null when unavailable |
| `livebench_coding` | LiveBench Coding average, 0–100; null without a reviewed model/effort match |
| `livebench_agentic_coding` | LiveBench Agentic Coding average, 0–100; null without a reviewed model/effort match |
| `livebench` | Source model, release, commit, retrieval time, effort, revision, agent, and completed/expected subtasks; null when unmatched |
| `math_index` | AIME 2025 math contest score (0–100). The site removed its Math Index, so this is the stand-in |
| `cost_per_task` | Cost to run one task of the AA Intelligence Index suite (USD) |
| `price_1m_input_tokens` | Input price per 1M tokens (USD) |
| `price_1m_output_tokens` | Output price per 1M tokens (USD) |
| `price_1m_cache_hit` | Cache hit price per 1M tokens (USD) |
| `blended_price_3_1` | Blended price at 3:1 input:output ratio |
| `context_window_tokens` | Context window size |
| `output_tokens_per_second` | Generation speed |
| `time_to_first_token_ms` | Latency to first token |
| `e2e_response_time_s` | Median end-to-end response time. Total seconds for a 500-token answer, with thinking time |
| `reasoning` | Whether it's a reasoning model |
| `open_weights` | Whether weights are open |
| `deprecated` | Whether Artificial Analysis marks the model as deprecated |

## Data coverage

| Metric | Coverage |
|---|---|
| Pricing (input/output) | 100% (388/388) |
| Intelligence Index | 98% |
| Cost per task | 36% |
| End-to-end response time | 82% |
| Speed (tok/s) | 82% |
| Cache pricing | 55% |

The site publishes `cost_per_task` only for a subset of endpoints. 137 models have all three plot metrics: intelligence, cost per task, and response time.

## How it works

```text
artificialanalysis.ai
  └─ /leaderboards/providers?_rsc=hgvan
       └─ Next.js RSC stream (~2.5 MB, text/x-component)
            └─ Contains "rows":[{...}] with ~1,100 entries
                 └─ Decode the JSON array with json.JSONDecoder().raw_decode
                      └─ Deduplicate by model slug (prefer the creator's own API)
                           └─ Clean & output models.json
```

The RSC endpoint requires specific headers (`rsc: 1`, `next-router-state-tree`, `next-url`) but no cookies or authentication.

## Limitations

- **No API key = fragile.** The RSC endpoint is an internal Next.js mechanism. If the site changes its chunk format again, the bracket-counting may need updating.
- **Placeholder values.** The RSC stream marks missing values with strings such as `"$undefined"`. The parser turns them into `null`. Some entries hold a reference string instead of a nested object. The deduplication step prefers entries with complete data.
- **Official API is preferred** for production use. This parser is a workaround for when you don't have (or don't want) an API key. See [artificialanalysis.ai/documentation](https://artificialanalysis.ai/documentation) for the free API tier (1,000 req/day).

## Companion: Intelligence Index vs. Cost per Task plot

`intelligence-vs-cost.html` replicates the scatter plot from the [artificialanalysis.ai](https://artificialanalysis.ai/) home page. Each point is one AI model. The X axis shows the cost to run one benchmark task (USD, log scale). The Y axis shows the AA Intelligence Index. A blue step line marks the Pareto frontier: the models that give the most intelligence for the money.

The Y axis can show six scores: the Intelligence Index, SciCode, the AIME 2025 math contest score, Terminal-Bench v4.0, LiveBench Coding, or LiveBench Agentic Coding. Use the radio buttons in the filter row to switch. The Pareto line follows the selected score.

Coding uses SciCode scaled to 0–100 because the models feed no longer supplies
the former composite Coding Index. These scores are not historically comparable.
Only models with SciCode scores appear in the Coding view. The `coding_index`
JSON key and `?metric=coding_index` link remain supported. The cost axis still
uses Intelligence Index task costs. A refresh with no chart-eligible SciCode
scores fails before replacing `models.json`, preserving the last usable data.

[Terminal-Bench v4.0](https://artificialanalysis.ai/evaluations/terminalbench-v4-0)
scores are downloadable in the existing models leaderboard RSC feed as
`terminalbenchV40`. The parser joins by exact model slug and scales fractions to
0–100. Zero is a valid score; missing scores are null and excluded from this
view. Select it with the radio button or `?metric=terminalbench_v4_0`.
The cost axis still uses Intelligence Index task costs, including any selected
subscription estimate. The response time filter uses the existing response-time
measurements, not Terminal-Bench task durations. This is internal page data,
not a supported CSV export or public API contract.

### LiveBench coding scores

The parser downloads the official [LiveBench score CSV](https://github.com/LiveBench/new-livebench/blob/main/public/table_2026_06_25.csv)
and [category map](https://github.com/LiveBench/new-livebench/blob/main/public/categories_2026_06_25.json)
for release `2026_06_25` from one resolved Git commit. The release date describes
the benchmark, not the last model addition. Each joined result records that commit
and its retrieval time in `livebench`, including in `--minimal` output.

Coding averages `code_generation` and `code_completion`. Agentic Coding averages
`javascript`, `typescript`, and `python`. These scores already use 0–100;
they are not multiplied by 100 or combined with SciCode. As in the
[official aggregation](https://github.com/LiveBench/new-livebench/blob/main/src/Table/Averaging.js),
missing subtasks are skipped. Zero is valid, and an entirely missing category
is null. The table and tooltips display completed/expected subtask counts so
partial results remain visible.

Select `?metric=livebench_coding` or `?metric=livebench_agentic_coding`, or use
the radio buttons. Both views use the existing provider/model selectors,
Pareto calculation, and response-time filter. Their cost axis is the AA
Intelligence Index task cost with the selected subscription adjustment, and
the response time is AA's measurement. Neither measures LiveBench evaluation
cost or duration.

The initial explicit mapping covers GPT-6 Astra max, GPT-5.6 Sol/Terra/Luna max,
Gemini 3.8 Flash high, and DeepSeek V4.1 Flash max. Identities and effort were
checked against LiveBench's
[model metadata](https://github.com/LiveBench/new-livebench/blob/bc7d9c1787d85ce521304fc0472fd8c25b117f75/src/Table/modelLinks.js)
and AA's model labels and slugs. Scores are never copied to other effort levels.
Fable 5.1's AA fallback variant and GLM-5.3's unspecified LiveBench effort are
not verified equivalents, so they remain unmatched. Other unreviewed IDs are
reported during refresh. Source coverage is broader than the current join.
`agent` and `model_revision` are null when the source does not supply them;
DeepSeek V4.1 Flash's published revision is retained.

The existing daily refresh command includes LiveBench automatically. Failed
acquisition, invalid schema/scores, conflicting duplicate rows or mappings,
or no chart-eligible scores in either added category abort before replacing
`models.json`. Unknown IDs are skipped and reported. Existing benchmark fields
and metric URLs retain their meanings; older JSON without LiveBench fields
still works in the page.

To reproduce a snapshot offline, supply all three LiveBench files alongside
the AA dumps. The metadata JSON contains `release`, the 40-character `commit`,
and an ISO 8601 `retrieved_at` with timezone. Use the CSV and category files from
that same commit, retaining the original retrieval time:

```bash
python3 artificialanalysis.ai-parser.py --minimal --pretty \
  --file providers.rsc --models-file models.rsc \
  --livebench-file livebench.csv \
  --livebench-categories-file livebench-categories.json \
  --livebench-metadata-file livebench-metadata.json
```

The focused fixtures under `tests/fixtures/` contain selected official rows and
category definitions; their metadata records the source commit and retrieval.
Run regression checks with:

```bash
python3 -m unittest discover -s tests -v
node --test tests/test_ui.cjs
```

The UI tests run the page's inline script with small DOM stubs in Node; they do
not verify browser layout.

The page adds one filter that the original site does not have: **maximum end-to-end response time**. Reasoning models can think for minutes before they answer. Move the slider to hide models that are slower than your limit. The page then computes the Pareto line again from the models that remain. This shows you the best value models that are also fast enough for your use case.

To use the page:

1. Run the parser to create `models.json`.
2. Start a web server in this folder: `python3 -m http.server`.
3. Open `http://localhost:8000/intelligence-vs-cost.html`.

The page has no dependencies. It also has a table view, tooltips, keyboard navigation, and a dark mode.

## License

GPL-3.0 — Copyright (C) 2026 Anton Maurer

## Credits

- Original scraping concept by [demianarc/artificialanalysisscrapper](https://github.com/demianarc/artificialanalysisscrapper)
- Model data source: [artificialanalysis.ai](https://artificialanalysis.ai)
