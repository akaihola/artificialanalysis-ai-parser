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
| `coding_index` | AA Coding Index, joined from the models leaderboard |
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

The Y axis can show one of three scores: the Intelligence Index, the Coding Index, or the AIME 2025 math contest score. Use the radio buttons in the filter row to switch. The Pareto line follows the selected score.

The page adds one filter that the original site does not have: **maximum end-to-end response time**. Reasoning models can think for minutes before they answer. Move the slider to hide models that are slower than your limit. The page then computes the Pareto line again from the models that remain. This shows you the best value models that are also fast enough for your use case.

To use the page:

1. Run the parser to create `models.json`.
2. Start a web server in this folder: `python3 -m http.server`.
3. Open `http://localhost:8000/intelligence-vs-cost.html`.

The page has no dependencies. It also has a table view, tooltips, keyboard navigation, and a dark mode.

## Companion: interactive cost calculator

`dashboard.html` — a dark-themed token cost dashboard that lets you see how much you'd spend using different AI model providers.

`compact-dashboard.html` — a lightweight version: no charts, 4 top models compared side by side. Each model card shows estimated total cost for your token data at a glance.

**Try it live:**  
[Full dashboard](https://maureranton.github.io/dashboard/dashboard.html) — charts, model selector, date range filter  
[Compact dashboard](https://maureranton.github.io/dashboard/compact-dashboard.html) — 4 models, instant cost comparison

**To run locally:**

1. Open `dashboard.html` or `compact-dashboard.html` in a browser (or serve via any HTTP server)
2. They load `paths.json` → `data.json` + `models.json`
3. Select a model — prices auto-fill from Artificial Analysis data
4. Tweak token counts — costs recalculate instantly

Example files included:
- `example-paths.json` — points to `example-data.json` and `models.json`
- `example-data.json` — 7 days of synthetic token data for demo

To use your own data, rename `example-paths.json` → `paths.json`, point it at your data file, and update your `data.json` with real token counts.

## License

GPL-3.0 — Copyright (C) 2026 Anton Maurer

## Credits

- Original scraping concept by [demianarc/artificialanalysisscrapper](https://github.com/demianarc/artificialanalysisscrapper)
- Model data source: [artificialanalysis.ai](https://artificialanalysis.ai)
