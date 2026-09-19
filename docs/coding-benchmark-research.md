# Coding benchmark data sources

Researched September 18, 2026.

Start with **LiveBench Coding and Agentic Coding**. Both have official, downloadable CSV data containing the current models from all five requested providers. **Code Arena WebDev** and **AI Coding Daily** also qualify.

This is research only. No parser or chart changes were made.

## Coverage requirement

I used a strict current-generation test: scored entries for GPT-6 Astra, Claude Fable 5.1, Gemini 3.8 Flash, GLM-5.3, and DeepSeek V4.1 Flash. These exact families occur together in the [official LiveBench results](https://github.com/LiveBench/new-livebench/blob/main/public/table_2026_06_25.csv), [Code Arena](https://arena.ai/leaderboard/code), and [AI Coding Daily](https://aicodingdaily.com/leaderboard). Reasoning settings differ and must remain attached to each result.

This deliberately excludes boards that represent all five companies only through older models. It does not assert that each company has just one frontier model. In particular, DeepSeek V4 Pro 0813 remains relevant, but a board containing only that release fails this stricter freshness test.

| Qualifying benchmark | OpenAI | Anthropic | Google | z.AI | DeepSeek |
| --- | --- | --- | --- | --- | --- |
| LiveBench Coding | Astra max | Fable 5.1 max | 3.8 Flash high | GLM-5.3 | V4.1 Flash max |
| LiveBench Agentic Coding | Astra max | Fable 5.1 max | 3.8 Flash high | GLM-5.3 | V4.1 Flash max |
| Code Arena WebDev | Astra max | Fable 5.1 max | 3.8 Flash high | GLM-5.3 max | V4.1 Flash max |
| AI Coding Daily | Astra medium | Fable 5.1 medium | 3.8 Flash high | GLM-5.3 high | V4.1 Flash max/high |

Coverage was checked against actual score rows, not model selectors or provider logos.

## Acquisition and estimated effort

Estimates are engineering time for one developer familiar with this repository. A prototype downloads and normalizes results; a maintained adapter adds fixtures, missing-value handling, model mapping, freshness checks, and refresh failure handling. Chart redesign and benchmark execution costs are excluded. These are estimates, not measured implementation times.

| Source | Existing GitHub implementation or data | Prototype | Maintained adapter |
| --- | --- | --- | --- |
| LiveBench, both coding categories | Official CSV/JSON and aggregation code in [LiveBench/new-livebench](https://github.com/LiveBench/new-livebench) | 2–4 hours together | 1–2 days together |
| Code Arena WebDev | [oolong-tea-2026/arena-ai-leaderboards](https://github.com/oolong-tea-2026/arena-ai-leaderboards), daily JSON snapshots and scraper | 2–4 hours consuming snapshots | 1–2 days consuming snapshots; 3–5 days for an independent scraper, subject to access constraints |
| AI Coding Daily | No dedicated public client or scraper found | 3–6 hours | 1–2 days |

### LiveBench Coding and Agentic Coding

Use the official data rather than scraping the React interface:

- [Score CSV](https://raw.githubusercontent.com/LiveBench/new-livebench/main/public/table_2026_06_25.csv).
- [Category definitions](https://raw.githubusercontent.com/LiveBench/new-livebench/main/public/categories_2026_06_25.json).
- [Release list](https://github.com/LiveBench/new-livebench/blob/main/src/lib/constants.js).
- [Model metadata](https://github.com/LiveBench/new-livebench/blob/main/src/Table/modelLinks.js).
- [Aggregation implementation](https://github.com/LiveBench/new-livebench/blob/main/src/Table/Averaging.js).

The downloaded CSV has nonempty scores for every required model in both categories. Coding averages `code_generation` and `code_completion`; Agentic Coding averages `javascript`, `typescript`, and `python`. Follow the published category map and averaging implementation, which skips nonnumeric values. Preserve missing-subtask counts so incomplete evaluations remain visible.

The `2026_06_25` filename identifies the benchmark release, not the last model addition. Its current contents include September models. Record the retrieval time and Git commit as well as the release date.

This is an official data feed through static files, not a dedicated REST SDK. The [evaluation repository](https://github.com/LiveBench/LiveBench) is for running evaluations; downloading score CSVs is sufficient for this project. The [website README](https://github.com/LiveBench/new-livebench/blob/main/README.md) documents the file layout and optional cost files. Both categories can share one fetch and parser.

### Code Arena WebDev

The [official leaderboard](https://arena.ai/leaderboard/code) measures preferences over generated web applications and agentic web-development outputs. It qualifies on model coverage, but its preference rating is a different measure from code-test pass rates. The page inspected was dated September 11, 2026.

An existing [Python scraper](https://github.com/oolong-tea-2026/arena-ai-leaderboards/blob/main/scripts/fetch_leaderboards.py) fetches pages through Jina Reader, extracts rows using OpenAI or Azure OpenAI, and validates JSON schemas. Running it requires an LLM API key; consuming its published files does not. It is not deterministic HTML parsing, so schema validation alone cannot guarantee accurate extraction.

Follow the [latest snapshot pointer](https://raw.githubusercontent.com/oolong-tea-2026/arena-ai-leaderboards/main/data/latest.json), then retrieve that date's `code.json`. I downloaded the [September 18 snapshot](https://raw.githubusercontent.com/oolong-tea-2026/arena-ai-leaderboards/main/data/2026-09-18/code.json) and verified all five required families and their scores against the official page. However, the snapshot contains **44 models**, while the page advertises **128**. Treat it as partial coverage. Preserve votes, confidence intervals, source update date, and snapshot date, and check required models on every refresh.

The repository also advertises a hosted REST endpoint at `api.wulong.dev`; that endpoint was not tested. Raw GitHub JSON was tested successfully. Direct Python requests to Arena returned HTTP 403 in this environment. An independent scraper therefore needs an access feasibility check before its effort estimate can be treated as reliable.

### AI Coding Daily

The [leaderboard](https://aicodingdaily.com/leaderboard) evaluates practical coding projects and publishes total points, project-level points, cost, time, and the agent used. The inspected table was updated September 15, 2026 and has all five required families. Different models use different agents, including Codex CLI, Claude Code, OpenCode, and Antigravity, so results measure model-and-agent combinations.

A direct HTTP GET succeeded and returned the complete table as HTML, including the model links and numeric cells. No browser execution was needed. A small `urllib.request` plus `html.parser` adapter fits this repository's standard-library approach. Match columns by headers and models by linked identifiers; handle `N/A` costs and durations, multiple effort settings, and changing project columns.

GitHub repository searches for `aicodingdaily` and `"AI Coding Daily" scraper` returned zero results. Web searches for the domain and leaderboard on GitHub also found no dedicated scraper. This establishes "not found," not proof that none exists. No documented score API was found. The table is small enough that writing a dedicated adapter is likely simpler than adopting a general scraping framework.

## Artificial Analysis and exclusions

The repository already supports SciCode and Terminal-Bench v4.0, so they are not new additions. Its checked-in data has SciCode scores for the five required families. Existing implementation support alone does not establish current Terminal-Bench score coverage.

The separate [AA coding-agent page](https://artificialanalysis.ai/agents/coding-agents) is promising: its [v1.5 methodology](https://artificialanalysis.ai/methodology/coding-agents-benchmarking) combines DeepSWE v1.1, Terminal-Bench 4.0, and SWE-Atlas-QnA. I downloaded its HTML and decoded the embedded Next.js stream. It contains 15 scored agent variants, including Astra, Fable 5.1, Gemini 3.8, and GLM-5.3, but its scored DeepSeek variants are V4 Pro 0813 and V4 Flash 0731. V4.1 Flash occurs only in the broader model metadata. **Do not mistake metadata presence for benchmark coverage.** This suite is excluded under the strict test.

If coverage catches up, the embedded records expose `displayLabel`, `hostModelSlug`, and per-benchmark `evals`, making an extension plausible in 1–2 days for a prototype, 2–4 days maintained. The existing [upstream AA parser](https://github.com/MaurerAnton/artificialanalysis-ai-parser) is reusable fetching/parsing groundwork, not a verified coding-agent client. The [documented AA API](https://artificialanalysis.ai/documentation) exposes model data; I did not find a documented coding-agent result endpoint. Do not assume the models API supplies these agent results.

Other screened boards did not establish the required coverage:

- [FrontierCode](https://cognition.com/frontiercode) lists Astra, Fable 5.1, Gemini 3.8, GLM-5.3, and DeepSeek V4 Pro 0813 in its changelog, but no verified V4.1 Flash result.
- [Datacurve DeepSWE](https://deepswe.datacurve.ai/) shows older Anthropic and DeepSeek entries in the inspected leaderboard. A vendor's separate model-card result does not establish a matching official leaderboard row.
- [FrontierSWE v2](https://www.frontierswe.com/) includes DeepSeek V4 Flash Vision Exp, not a verified V4.1 Flash row. Do not alias those releases without evidence.
- [Scale SWE-Atlas-QnA](https://labs.scale.com/leaderboard/sweatlas-qna) shows DeepSeek V4 Pro and GLM-5.2/5 rather than the required current pair.
- [Aider Polyglot](https://aider.chat/docs/leaderboards/) has older model generations. [LiveCodeBench](https://livecodebench.github.io/leaderboard.html) and [SWE-bench](https://www.swebench.com/) did not expose verified all-five current-model coverage in the inspected pages. They are unqualified here, not claims that newer results cannot exist elsewhere.
- [Arena Agent](https://arena.ai/leaderboard/agent) has current coverage, but combines signals from general agent use. It was excluded as insufficiently specific to coding.

## Integration recommendation

Add the two LiveBench categories first, then AI Coding Daily. Use Code Arena when preference over web-development outputs is useful, with explicit partial-snapshot detection.

Keep benchmark version, source, agent, model revision, and reasoning effort with every score. Never average these different benchmarks into the existing `coding_index`. Keep rating scales and pass-rate scales distinct. If scores use the current Intelligence Index cost axis, label that cost basis explicitly; it is not the cost of running these coding benchmarks. AI Coding Daily and AA agent results offer their own task costs, but those costs belong to their respective evaluations.

Validation performed: downloaded and parsed official LiveBench CSV/category files, inspected its aggregation code, downloaded and checked Arena snapshot rows, fetched AI Coding Daily's HTML table, decoded AA's scored agent records, and inspected the reusable scraper source. No evaluation runs, paid API calls, or scraper implementation were performed.
