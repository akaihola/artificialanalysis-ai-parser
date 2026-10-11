# Completeness critique of the slopalytics rebuild reports

Date: 2026-10-11. Reviewed reports: `aa-payload.md`, `mapping.md`, `logos.md`, `chart-spec.md`, `sidebar-spec.md` (all present).
Spot-checked against `bundle.pretty.js` (lines 11892, 28602-28830, 29077-29275, 30078-30760, 30796-30960, 31031-31619), `style.pretty.css`, slopalytics `models.json`, our `models.json` (local `master` and `origin/master`), `artificialanalysis.ai-parser.py`, `intelligence-vs-cost.html`, `tests/test_ui.cjs`, `tests/test_firefox.cjs` and `.github/workflows/update-models.yml`.
Check scripts are in `/tmp/claude-1002/slopalytics-facts/scripts-critique/` (`check1.py`-`check4.py`, run with `python3 -I`). `downloads-critique/origin-master-models.json` is `git show origin/master:models.json`.

## 0. Verified (no action needed)

All of these matched the source exactly:

- Chart formulas in `chart-spec.md`: the `Qn` layout constants, domains, `nice()` ticks, log mantissas, opacity rules `pe`/group/label, label anchor and spacing pass, crosshair geometry, tooltip metric list, `Kt` formatter, `R` multiplier, Pareto `Yt`, the Escape handler, and the mobile tap radius of 40.
- Tooltip CSS: 272/400 px wide, `inset: auto 8px 72px auto`, mobile sticky grid.
- Sidebar: the `nr`/`rr`/`ar`/`or`/`sr` derivation, the `Xt` comparator, the effort list `me`, the Other-group filter, the tier and "All" toggles, the `P()` reset versus header reset (`P(); l(null)`), the context-menu items, the nuqs keys, defaults and `eq`, and the legacy `#view` migration.
- Dataset facts:
  - 696 models and 502 families: 10 Frontier, 7 Notable, 485 Other.
  - Effort counts: none 294, default 220, high 57, low 31, medium 30, xhigh 30, max 30, minimal 4.
  - Default view: 34 visible variants, intelligence 21.53-57.62.
  - Frontier and Notable display orders, and the Other counts 36/133/316.
  - Paint order: Fable, Haiku, Opus, Argon, Sol, Astra, Luna, Grok.
  - Family-level fields are consistent inside every family (0 exceptions). The only family+effort collision is `claude-sonnet-4-6`/`none`.
- Logos: the anthropic and openai embedded SVGs are byte-identical to the svgl files; the 9 files total 17,659 B.
- The models leaderboard (`models.rsc`) holds 2 `"models":[` arrays (697 nav, then 697 leaderboard). The nav array carries `releaseSlug`; the leaderboard carries `shortName`, `isReasoning` and `modelCreatorColor` but no effort.

## 1. Contradictions and errors (with the correct value)

1. **"Our models.json is 17 days stale; 4 Frontier families missing; 29 cost entries absent" (`mapping.md` §1, §5). This is wrong for the repo as a whole.**
   - Local `master` (13f48ad) and `origin/master` (dd93ae6) have diverged at merge-base 3278dea. Local holds 20 UI commits that are not on origin. Origin holds 17 daily `chore: update models.json` commits that are not on local, the last on 2026-10-11 03:39 UTC.
   - `origin/master:models.json` has 445 models and 181 with `cost_per_task`, all 181 joining slopalytics `id`. **All 10 Frontier families are present with cost**, including gpt-6-1-sol ×5, claude-sonnet-5-5 ×5, claude-haiku-5-5 ×5, gemini-4-argon and grok-4-7-low.
   - Costs equal slopalytics for 149/181 and intelligence for 179/181. `deprecated` differs for 1 entry only, not 17.
   - The fix is to bring origin's data into the work branch, not to re-scrape.
2. **`mapping.md` §2, "four of these … the other five".** Of the 9 effort mismatches, only **three** (gemini-3-5-flash, gemini-3-6-flash, inkling) have the effort in the leaderboard `shortName`/`name`. "Qwen3.8 27B (xhigh)" is not one of the 9. The remaining **six** need the model page: gemini-3-5-flash-lite, gemini-3-1-flash-lite-preview, mistral-medium-3-5, solar-pro-3, ring-2-6-1t and glm-5-3-flash. The leaderboard names of these six carry no effort (checked in `downloads-aa/models.rsc`).
3. **`mapping.md` name rule step 1 ("strip a trailing ` AI Studio`/` Vertex`") fails on current data.** Origin's name is `Gemini 4 Argon (high) AI Studio (1M output)`. Our HTML's `baseModelName()` already mis-groups it as `Gemini 4 Argon (high) AI Studio`. Use `releaseSlug` from the nav block instead of any name heuristic.
4. **`aa-payload.md` §7: "`agentic_index` is null for all 426 models".** The key is in fact **absent**. The daily workflow runs `--minimal --pretty`, and `compress_for_calculator()` drops `agentic_index`, `gpqa` and `hle`. Consequence that no report states: **any new field (family, lab slug, effort, released, …) must be added to the `keep` list in `compress_for_calculator`**, or the daily job strips it.
5. **`chart-spec.md` §3: "Cost ranges $0.0047-$7.63, xMin ≈ 0.0033".** The minimum is $0.004517 (gpt-6-luna-low), which gives xMin ≈ 0.00316. The ticks are unaffected.
6. **`chart-spec.md` §12 / `sidebar-spec.md` §10: "lab items for a lab-only opener".** No caller passes a lab without a model; `j()` is called only as `j(e)` (empty SVG) or `j(e, model)`. Lab items therefore appear only with a model. The menu title fallback uses `rr` `labName` ("SpaceXAI"), while the item labels use the `Bt` name ("xAI").
7. **`chart-spec.md` §6: "Points have no focus ring".** The rule `.chart-svg g[role=button]:focus{outline:none}` also matches the **right-side series labels** (they are `g[role=button]`). Keyboard focus on a label is visible only through the emphasis that `T` triggers.
8. **`chart-spec.md` §2: "The SVG fills `.chart-canvas` (flex:1)".** The spec omits that `.chart-canvas{position:relative}` and `.chart-canvas>svg{position:absolute;inset:0}`, and that `.chart-wrap` is a `position:relative` flex column. Without the absolute SVG, the ResizeObserver can feed back on the SVG's own size.
9. **`logos.md` coverage counts (39 creators, 426 models)** are based on the stale local file and count every creator. Only **25 creators have cost rows** in origin data (23 locally), and **Nous Research (19.6 KB sprite) has none**. The Sapiens AI creator has dropped out. Logo budget only matters for plotted creators, unless the sidebar lists unplottable families (see D11).
10. Minor inconsistencies:
    - `aa-payload.md` gives 182 non-null efforts and `mapping.md` gives 183. Both are right: 696 snapshot versus 697 live (`gpt-6-sol-daybreak-blue`).
    - `intelligence` is "694/696" in one report and "685/687" in the other. These are the same 2 misses with different denominators.

## 2. Facts still missing for a faithful clone that keeps our features

### Data and scraper

- **Fields the UI actually reads.**
  - Read: `id, family, name (=release name), lab (slug), labName, released, open, deprecated, effort, effortLabel, effortOrder, intelligence, cost, tokens, time`.
  - Never read: `variant`, `estimated`, `speed`, `context`, `inputPrice`, `outputPrice`. Do not spend scraper effort on them for this chart.
- **Lab slug.** It is required because colours, logos, the monochrome set and the sort all key on `lab` (`xai`, not "SpaceXAI"). Only `nav.releases[].creator.slug` has it.
- **Paint and tab order.** The slopalytics dataset is sorted exactly by `id.casefold()`. Our scraper sorts by intelligence descending. To match line overlap and Tab order, sort rows by slug (case-insensitive) in the page.
- **Model-level e2e.** The leaderboard has a per-variant `medianEndToEndResponseTimeSeconds`: 171 of 186 cost rows have it. If cost switches to model-level `intelligenceIndexCostPerTask` (for slopalytics parity), take e2e from the same object, so the slider filters on the same host basis as the cost.
- **Null e2e in Frontier families.** In origin data, gemini-4-argon (the whole family), gpt-6-luna-medium, gemini-3-8-flash-medium, gpt-6-sol-medium, mistral-large-4 and apodex-1-1 have cost but null e2e. The current rule ("unknown time stays visible", asserted in `tests/test_ui.cjs`) keeps them visible at every slider value.
- **Zero-price models.** The scraper drops price-0 models (`if m["price_1m_input_tokens"] and …`). The 7 cost-0 models in slopalytics would not exist in our data. In log mode slopalytics hides them anyway; a Linear mode would differ.
- **Model-page source is fragile.** The full 697-object list appears only on pages that render `LanguageModelCompareButton`, i.e. models without effort variants (`/models/gpt-4-1`, a deprecated model). Pages with variants carry 26 objects. If tokens and time per task are wanted in the tooltip, the scraper needs a fallback slug list and a sanity check (≥ N objects with `intelligenceIndexEvaluations`).
- **Tokens and time per task** (tooltip rows 3-4 for the cost chart) are not in our payloads. Either fetch the model page or replace those rows.

### Rendering and CSS

- See items 7 and 8 above (focus outline scope, absolute SVG).
- Our existing CSS conflicts with the slopalytics markup. These rules override what it expects: `svg text, svg path, svg line {pointer-events:none}`, `svg {height:auto}` and `svg text {font-family: system-ui}`. They must be removed or scoped.
- **Firefox support for `light-dark()` in SVG presentation attributes is unverified.** The repo has a Firefox Playwright test. Set family colours via `style.fill`/`style.stroke`, or resolve the hex value in JS.

### Tests that encode current behaviour

- **`tests/test_ui.cjs` runs the inline `<script>` in a `vm` context with a hand-made fake DOM.** That DOM has no `matchMedia`, `ResizeObserver`, `getScreenCTM`, `DOMPoint`, `document.documentElement`, `innerWidth`, or real `querySelectorAll`. Slopalytics patterns such as top-level `matchMedia('(max-width: 900px)')` will throw at load. The harness must be extended, or those calls guarded.
- **Assertions that will break:**
  - provider-grouped picker markup (`data-provider`, `data-key="OpenAI::Best"`, "Models: 5 of 5 selected")
  - "Reasoning levels share one row"
  - a compact `models` URL value shorter than the joined keys
  - `metric` URL param
  - LiveBench provenance text "2026_06_25 · test-max · 1/2 subtasks"
  - table rows `<td>Name</td>`
- The test fixtures lack `family`/`lab`/`effort` fields, so the new code must tolerate missing fields or the fixtures must be updated.
- `tests/test_firefox.cjs` tests the provider bulk toggle and URL restore through `#model-picker-toggle`.

### Kept features with no slopalytics counterpart (behaviour must be specified)

- **Benchmark selector.** Everything that hard-codes `intelligence` must follow the selected metric:
  - the y title "Intelligence index"
  - `aria-label`s
  - the label anchor ("highest-intelligence variant")
  - the visible-set filter `intelligence !== null`
  - the crosshair label formatter
  - the Pareto y value
  - the tooltip's first row

  Slopalytics' y clamps (`min(...,30)`, `max(...,50)`) were tuned for the AA index.
- **Coverage per metric under the slopalytics default selection** (8 families, effort `none` hidden), origin data:

  | metric | points |
  |---|---|
  | Intelligence | 34 |
  | SciCode | 34 |
  | Terminal-Bench v4.0 | 34 (min 0) |
  | LiveBench Coding / Agentic | **1** (GPT-6 Astra max). The other 5 LiveBench rows are gpt-5-6-sol/terra/luna, gemini-3-8-flash and deepseek-v4-1-flash, none of them default-selected; 2 are deprecated. |
  | Math (AIME 2025) | **0**, so the empty state "No data for this view" appears. Only 19 cost rows have AIME. |

- **Plan multipliers break the slopalytics cost formatter.**
  - The formatter `Kt` uses `maximumFractionDigits: 3` below $1.
  - Under ChatGPT Pro (÷20), gpt-6-luna-low costs $0.000226. Its tooltip shows "$0.00", and the x ticks at 0.0002 and 0.0001 render "$0" while 0.0005 renders "$0.001" (verified in node).
  - Use significant-digit formatting (the current `fmt$` uses `toPrecision(2)`).
  - The comparison "Multiplier" column and the PNG aria text must use the effective cost, not the raw `cost`.
- **Plan keying.** Plans are applied by `provider` (host): OpenAI 46, Anthropic 35, plus 2 OpenAI-creator gpt-oss rows on CoreWeave that correctly get no plan. Model-level data has no host. If the key moves to `lab`, gpt-oss would wrongly get ChatGPT Plus/Pro pricing.
- **Tooltip.** The slopalytics panel sits at a fixed bottom-right position, 272 px wide (400 px when comparing). Ours lists 11 rows: 6 scores, plan cost, API cost, response time, prices, speed, plus LiveBench `<small>` provenance. The comparison table has no place for provenance.
- **Table view, fullscreen, show-deprecated, Y-zoom, status line, help text and touchpad horizontal-wheel slider nudge** are absent from slopalytics. Their placement in the 100dvh grid (non-scrolling document, sidebar 248 px, heading controls row) is unspecified.

## 3. Conflicts that need a human decision

D1. **Default selection.**
- Slopalytics: 8 hand-picked Frontier families, with `none` effort hidden.
- Ours: every cost model selected.
- The curated `L`/`Rt` lists go stale under daily data updates (new releases appear in origin within days).
- Options:
  - keep a hand-maintained config
  - derive Frontier automatically (e.g. the newest top-intelligence release per major lab)
  - default to all families

D2. **Default selection versus the benchmark selector.** Under D1-style defaults, LiveBench shows 1 point and Math shows an empty state. Options:
- per-metric default selections
- auto-add families that have data for the metric
- a hint in the empty state
- drop Math (AIME, 19 rows)

D3. **URL `models` key collision.**
- Ours: a positional hex bitmask over sorted provider::name keys. It is rejected when the key count changes, so shared links break with each daily data change.
- Slopalytics: a comma list of family slugs. It is robust but not "condensed", and condensed is the TASKS.md preference.
- Old hex links parsed with slopalytics rules would become `[]` and show "No models selected".
- Options:
  - rename the key
  - detect hex and fall back to the default
  - a condensed but stable encoding (e.g. a short family-id list or base64 of a sorted-slug bitset with a dataset hash)

D4. **Selection granularity.**
- Slopalytics selects by family (AA release) and lab. Ours selects by provider (host) and base name.
- TASKS.md wants "select/deselect all models for a provider with one or two clicks". Slopalytics offers that only through the right-click menu ("Show only/Hide {Lab}"), which is invisible on touch and undiscoverable.
- Decide whether to add visible per-lab toggles to the sidebar.

D5. **Visual encoding of the Pareto concept.**
- Ours: the Pareto line is always on, as a step line in a series colour. Points are coloured Pareto versus grey, and only Pareto points get labels.
- Slopalytics: family-coloured effort lines with right-gutter family labels (max 16). Pareto is opt-in (`frontier=false` by default), drawn as straight dashed segments in `--fg`.
- Choose the default `frontier` state, the segment style (step or straight), and the label scheme (family labels or Pareto labels).

D6. **Ghost dots (time filter) inside the slopalytics opacity system.** Slopalytics already uses .15, .25, .4 and .45 for de-emphasis; our ghosts use .22.
- Decide whether ghosts are family-coloured, hollow or grey.
- Decide whether family lines extend through ghosts.
- Decide whether ghosts are hit-testable or tooltipped.
- Decide whether the right-label anchor jumps to a non-ghost variant while the slider moves.

D7. **Axis domains.**
- Slopalytics computes x and y from the visible set `O`, so the axes rescale on every selection change and would rescale continuously while dragging the time slider.
- Ours uses fixed domains from the whole dataset unless Y-zoom is on.
- Options: visible ∪ ghosts, visible only, or fixed.
- Y-zoom-to-Pareto must bypass the slopalytics clamps (yMin ≤ 20 via `min(...,30)`, yMax ≥ 55 via `max(...,50)`) or it will barely zoom. Decide whether zoom requires the Pareto toggle to be on.

D8. **Show-deprecated semantics.**
- Slopalytics: deprecated is a family-level listing filter ("Older" under "Show all models"), and selected deprecated families are plotted with dashed lines.
- Ours: a global chart filter that hides deprecated points even when selected.
- Options:
  - map the toggle to "Older"
  - keep it as a chart filter (the "Models N" count then disagrees with the plot)
  - keep both

D9. **Where our extra controls go.**
- Controls to place: 6-metric selector, 2 plan selects, the time slider with its number box, show-deprecated, Y-zoom, table, fullscreen.
- Candidate locations: `.chart-controls` in the heading (already holds Pareto and Linear/Log), the 211 px sidebar, or a second toolbar.
- Fullscreen must "include filters" (TASKS.md): either fullscreen the whole `.app` (header, chart and sidebar), or move the filters into the chart section.

D10. **Table view and help text placement.** The slopalytics desktop layout is a 100dvh grid with no document scroll and one full-height section per chart. Options for the table and the help text (subscription-pricing explanation, metric definitions):
- a second `.chart-section` in the feed
- a toggle that replaces the canvas
- a footer page below the grid

D11. **Sidebar scope.** Slopalytics lists families that have no data for the current chart. Ours has 445 models but only 181 with cost.
- Decide whether to list unplottable families.
- This affects the logo budget (Nous Research and others) and search noise.

D12. **Time semantics.**
- The slopalytics tooltip and second chart use index "Time per task" (`intelligenceIndexTimePerTask`, e.g. 784 s for Opus max).
- Our slider and tooltip use per-request `e2e_response_time_s` (667 s for the same model, 15.7 s versus 81.8 s for Opus low).
- Decide labels, and whether to fetch time and tokens per task from the model page.

D13. **Cost source.**
- Model-level `intelligenceIndexCostPerTask` matches slopalytics for 181/186 rows.
- Our per-host dedup picks the cheapest third-party host (e.g. gpt-oss-120b 0.023 versus 0.107), and its first-party test fails for Alibaba/Alibaba Cloud, Z AI/Zai, Amazon/Amazon Bedrock and Microsoft/Microsoft Azure.
- Switching to model-level cost changes the plan keying (see §2, plan keying).

D14. **Theme and fonts.**
- Slopalytics is dark by default, not persisted, and ignores `prefers-color-scheme`. It loads DM Sans from Google Fonts (an external request).
- Our page follows the OS preference and has no external requests.

D15. **Escape key overlap.** Slopalytics' window Escape clears pins and **all highlights**; ours exits fallback fullscreen and closes the picker. Define the priority order.

D16. **Logo licensing.** The svgl-derived marks have no per-logo licence; lobehub is MIT and needs a notice; simple-icons is CC0 but carries trademark caveats. The options are the 9 slopalytics logos as-is, a lobehub mono sprite (≈12.6 KB gzip without Nous), or monograms only.
