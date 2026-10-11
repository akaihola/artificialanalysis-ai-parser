# Our models.json vs slopalytics models.json: mapping facts

Inputs:
- Ours: `/home/agent/repos/ai/artificialanalysis-ai-parser/models.json`. Last commit d907ae7 on 2026-09-24, 426 entries, 152 with `cost_per_task`.
- Theirs: `/tmp/claude-1002/slopalytics-research/models.json`. `fetchedAt` 2026-10-08T02:04Z, `source` https://artificialanalysis.ai/models/gpt-4-1, 696 entries, 185 with `cost`, 502 families.
- Live AA cross-check, downloaded 2026-10-11 04:10Z into `/tmp/claude-1002/slopalytics-facts/downloads-mapping/`:
  - `providers.rsc`: the providers leaderboard that our scraper uses
  - `models.rsc`: the models leaderboard that our scraper also fetches
  - `model-page.rsc`: `/models/gpt-4-1?_rsc`, the slopalytics source
- Scripts are in `/tmp/claude-1002/slopalytics-facts/scripts-mapping/`: `analyze.py`, `extra.py`, `history.py`, `live*.py`, `family_r4.py`. Their raw outputs are in `out*.txt` in the same directory.

## Key discovery: where slopalytics' fields come from

Every AA `/models/<slug>` page RSC embeds about 697 model objects. I checked them against the live page on 2026-10-11. The table below lists exact matches over 696 entries:

| slopalytics field | AA model-page field | exact |
|---|---|---|
| `id` | `slug` | 696 |
| `family` | `release.slug` (also `releaseSlug` in the models leaderboard) | 696 |
| `name` | `release.name` | 695 (exception: GLM-5.3-Flash vs their "GLM 5.3 Flash") |
| `variant` | `shortName` | 696 |
| `released` | `releaseDate` | 696 |
| `effort`/`effortOrder`/`effortLabel` | `effort.slug`/`effort.level`/`effort.label`. If `effort` is null: `isReasoning` gives `default`/35/"Default", otherwise `none`/0/"Non-reasoning" | 696 |
| `lab`/`labName` | `creator.slug`/`creator.name` | 696 |
| `open` | `isOpenWeights` | 696 |
| `context` | `contextWindowTokens` | 696 |
| `intelligence` | `intelligenceIndex` | 685/687 |
| `cost` | `intelligenceIndexCostPerTask.cost.total` (the models leaderboard has the same value as flat `intelligenceIndexCostPerTask`) | 175 exact, 10 drifted |
| `costTotal` | `intelligenceIndexCost.total` | 175 exact |
| `tokens` | `intelligenceIndexOutputTokensPerTask.output` | 198 exact |
| `tokensTotal` | `canonicalIntelligenceIndexTokenCount.output` | 198 exact |
| `inputPrice`/`outputPrice` | `price1mInputTokens`/`price1mOutputTokens` | 458/456 of 464 |
| `estimated` | `intelligenceIndexIsEstimated` | 695 |
| `time` | close to `intelligenceIndexTimePerTask`, never exact | – |

The models leaderboard, which our scraper already downloads (`MODELS_RSC_URL` in `extract_model_indexes`), has these fields:
- `releaseSlug`, equal to their `family` for 696/696
- `shortName`
- `name`, with the effort capitalised, e.g. "Gemini 3.5 Flash (High)"
- `isReasoning`, `deprecated`
- flat `intelligenceIndexCostPerTask`: model-level, and the same as their `cost`

It has **no effort field**. Only the model page (3.2 MB) carries `effort {slug,label,level}`. The effort levels are minimal 10, low 20, medium 30, high 40, xhigh 50, max 60. 183 models have a non-null effort.

## 1. Join: slug == id

- **152/152 of our cost entries match a slopalytics `id` exactly.** No normalisation is needed.
- 150/152 joined entries have a non-null `cost` on their side. The two that do not are `inkling` and `minimax-m2-7`.
- 35 of their cost entries are not in our cost set:
  - **29 are absent** from our models.json. Most are new releases after our 2026-09-24 snapshot: claude-sonnet-5-5 ×5, claude-haiku-5-5 ×5, gpt-6-1-sol ×5, gemini-4-argon, grok-4-7-low, glm-5-3-low, deepseek-v4-pro-non-reasoning, deepseek-v4-1-flash-non-reasoning, ling-3-1-flash, mimo-v2-6-flash, mistral-large-4, solar-mini4, k2-horizon. Some are older entries that are missing from the providers feed: command-a-plus, gemma-4-31b, north-mini-code, ling-3-0-tiny. Those, plus gemma-3-12b and gemma-3-27b, have **cost 0** in their data because the price is 0.
  - **6 are present in ours without cost:** apodex-1-1, deepseek-v4-flash-0420-high, inkling-small, kimi-k3-low, qwen3-5-9b, trinity-large-thinking.
- The live providers feed (2026-10-11) contains every missing Frontier/Notable slug with a cost. A re-scrape would close most of the gap. **Our models.json is 17 days stale.**

## 2. Effort suffixes

### Parentheticals in our 152 cost names (counts)

| parenthetical | n | proposed effort (order) |
|---|---|---|
| (none) | 50 | `reasoning` true → default (35), false → none (0) |
| (max) | 21 | max (60) |
| (high) | 19 | high (40) |
| (xhigh) | 17 | xhigh (50) |
| (medium) | 12 | medium (30) |
| (low) | 10 | low (20) |
| (Non-reasoning) | 5 | none (0) |
| (max with fallback) | 2 | max (60) |
| (xhigh with fallback) | 2 | xhigh |
| (high with fallback) | 2 | high |
| (medium with fallback) | 2 | medium |
| (low with fallback) | 2 | low |
| (with fallback) | 1 | **max (60): ambiguous**; AA suffix is "Max, Opus 4.8 Fallback" |
| (0902), (June 2026), (Jan), (Dec) | 1 each | not effort; ignore, then use the reasoning flag |
| (AI Studio), (Vertex) | 1 each | host label; ignore |
| (BF16) | 1 | precision; ignore |

Name quirks:
- Some names have text after the effort parenthetical: "Gemini 3.7/3.8 Flash (high|medium) AI Studio".
- Some names have a bare host suffix: "Gemini 3.5/3.6 Flash AI Studio", "Gemini 3.5 Flash-Lite AI Studio", "Gemini 2.5 Pro Vertex".

These come from our dedup taking the *shortest host label*. So the effort can sit mid-string, and the label is sometimes host-specific.

Other parentheticals in all 426 of our names, which matter if the rule is applied beyond cost entries:
- (Non-reasoning, high) ×3 and (Non-reasoning, low) ×1 → none
- (Reasoning) ×6 → default
- (minimal) ×4 → minimal (10)
- (FP8) ×6, (Preview) ×2, (Vision), month names (May, Sep, Oct, …), (May 2026) → ignore

### Trailing slug segments in our 152 cost slugs

| segment | n |
|---|---|
| no suffix | 79 |
| -medium | 14 |
| -xhigh | 12 |
| -high | 12 |
| -low | 12 |
| -non-reasoning | 6 |
| -reasoning | 4 (not effort) |
| -max | 2 (**not effort**: qwen3-7-max and qwen3-8-max are model names) |
| -preview | 2 |
| -thinking, -adaptive, -vision | 1 each |
| dates: -0803, -0424, -06-26, -0420, -0120, -0324 | 1 each |

The slug alone cannot give the effort. Base slugs with no effort suffix are max 23, high 9, xhigh 7, bare-fallback 1, and 56 with no effort in the name. Where a slug suffix exists, it always agrees with the name.

### Proposed deterministic rule (name-based)

1. Strip a trailing ` AI Studio` or ` Vertex`, with or without parentheses.
2. For each parenthetical, lower-case it and remove a trailing ` with fallback`:
   - `non-reasoning` or `non-reasoning, *` → none
   - a value in {minimal, low, medium, high, xhigh, max} → that value
   - a bare `with fallback` → max (ambiguous)
3. Otherwise, `reasoning` false → none (0), and true → default (35).
4. Set effortOrder from {none 0, minimal 10, low 20, medium 30, high 40, xhigh 50, max 60, default 35}.

This matches 143/152 of the joined entries, and the effortOrder agrees each time. There are **9 mismatches**. In every one, the name carries no effort but AA has an explicit `effort`:

| slug | our name | ours | theirs |
|---|---|---|---|
| gemini-3-5-flash | Gemini 3.5 Flash AI Studio | default | high |
| gemini-3-6-flash | Gemini 3.6 Flash AI Studio | default | high |
| gemini-3-5-flash-lite | Gemini 3.5 Flash-Lite AI Studio | default | high |
| gemini-3-1-flash-lite-preview | Gemini 3.1 Flash-Lite (AI Studio) | default | high |
| mistral-medium-3-5 | Mistral Medium 3.5 | default | high |
| solar-pro-3 | Solar Pro 3 | default | high |
| inkling | Inkling | default | xhigh |
| ring-2-6-1t | Ring-2.6-1T | default | xhigh |
| glm-5-3-flash | GLM-5.3-Flash | default | max |

For four of these, the models-leaderboard `shortName` or `name` carries the effort: "Gemini 3.5 Flash (high)", "Gemini 3.6 Flash (high)", "Inkling (xhigh)", "Qwen3.8 27B (xhigh)". The other five (Flash-Lite ×2, Mistral Medium 3.5, Solar Pro 3, Ring, GLM-5.3-Flash) only have the effort in the model page's `effort` object.

**Exact alternative:** fetch `/models/<any-slug>?_rsc` and read `effort` and `isReasoning`. This reproduces their effort for 696/696.

Other ambiguities to flag:
- Bare `(with fallback)` maps to max.
- A slug ending in `-max` is not effort.
- AA's own data has a family+effort collision: family claude-sonnet-4-6 has two `none` variants, "(non-reasoning, high)" and "(non-reasoning, low)". Both have null cost.
- Their `effortLabel` is lower-case for explicit efforts, but "Default" and "Non-reasoning" for the fallbacks.

## 3. Family rule

| rule | exact vs their family (joined) | our cost entries in *some* their-family |
|---|---|---|
| R1: strip `-(non-reasoning\|minimal\|low\|medium\|high\|xhigh\|max)$` | 140/152 | 140/152 |
| R2: R1, then strip `-(reasoning\|thinking\|adaptive)$` | 142/152 | 144/152 |
| R3: slugify(name without effort/host parentheticals) | 138/152 | 141/152 |
| R4: R2 but never strip `-max` | 143/152 | 146/152, including 3 *wrong-family* hits |
| R4 + 9-entry alias table | 152/152 | 152/152 |
| **AA `releaseSlug` from the models leaderboard (already fetched)** | **696/696 in their whole dataset** | – |

R2 produces 8 families that match none of theirs: `gemini-3-1-flash-lite-preview`, `gemma-3-12b`, `gemma-3-27b`, `nvidia-nemotron-3-ultra-550b-a55b`, `qwen3-7`, `qwen3-8` (both from stripping "-max"), `qwen3-8-max-0803`, `step-5`.

R4 leaves 6 families that match none of theirs: step-5, qwen3-8-max-0803, nvidia-nemotron-3-ultra-550b-a55b, gemini-3-1-flash-lite-preview, gemma-3-12b, gemma-3-27b. It also has 3 false positives that land in the wrong family:
- qwen3-8-max → qwen3-8-max. Their family for it is qwen3-8-max-0902; their `qwen3-8-max` family belongs to slug qwen3-8-max-0803.
- qwen3-235b-a22b-instruct-2507-reasoning and qwen3-30b-a3b-2507-reasoning. Stripping `-reasoning` merges them into the instruct families. AA keeps those separate but does merge claude-4-5-haiku-reasoning into claude-4-5-haiku.

The alias table (slug → family) needed on top of R4:
- qwen3-8-max → qwen3-8-max-0902
- qwen3-8-max-0803 → qwen3-8-max
- step-5 → step-5-preview
- nvidia-nemotron-3-ultra-550b-a55b → nemotron-3-ultra-550b-a55b (the super and nano variants keep the `nvidia-` prefix)
- gemini-3-1-flash-lite-preview → gemini-3-1-flash-lite (gemini-3-1-pro-preview keeps `-preview`)
- gemma-3-12b → gemma-3-12b-instruct
- gemma-3-27b → gemma-3-27b-instruct
- qwen3-235b-a22b-instruct-2507-reasoning → itself
- qwen3-30b-a3b-2507-reasoning → itself

AA's release grouping is arbitrary, so the **recommendation is to keep `releaseSlug`** (plus `shortName` and `name`) from the models leaderboard in our scraper. No heuristic is needed then. With the correct families, there are 96 distinct families among our cost entries, 17 of them with more than one variant, and no family+effort collisions.

## 4. Value comparison (150 joined entries with cost on both sides)

| ours vs theirs | equal | differ | max abs diff |
|---|---|---|---|
| cost_per_task vs cost | 90 | 60 | 2.131 (gemini-3-5-flash: 1.5625 vs 3.6937) |
| intelligence_index vs intelligence | 140/152 | 12 | 0.869 |
| input/output price | 130 | 22 | 1.3 / 2.52 |
| context | 108 | 44 | 744000 |
| open | 152 | 0 | |
| deprecated | 135 | 17 | |

The 17 `deprecated` differences are all theirs=true, ours=false: gpt-6-sol ×6, grok-4-6 ×4, claude-sonnet-5 ×5, mimo-v2-5-pro, mistral-large-3. AA marked these deprecated after the newer releases.

Equal values are identical to the last bit, so both datasets come from **the same AA backend**. The differences have two causes.

**(a) Snapshot drift, 2026-09-24 vs 2026-10-08:**
- All 12 intelligence differences are GPT-6 Sol/Luna. They were re-scored, and the live AA value equals theirs.
- 19 first-party entries have the same prices and intelligence but a different cost. These are 5 Gemini, 5 Grok, claude-4-5-haiku, gpt-5-4-mini, mistral-medium-3-5, mistral-large-3, mercury-2-5, qwen3-7-plus and others. Our value had been stable for at least 14 daily commits. The live providers feed now shows their value on the first-party host, so AA changed these costs after Sep 24.

**(b) Granularity, model-level vs host-level:**
- Their `cost` and prices are AA's model-level `intelligenceIndexCostPerTask`, which uses AA's representative host and price.
- Ours is one providers-leaderboard host row picked by our dedup, which prefers the cheapest host when it sees no "first-party" host.
- 29 of the 39 third-party-host entries differ for this reason, e.g. gpt-oss-120b: CoreWeave 0.023 vs model-level 0.107; qwen3-coder-next: 0.123 vs 0.552.

Breakdown of the 150 entries:
- first-party host: 80 equal, 31 differ (12 GPT-6 re-scored, 19 cost drift)
- third-party host: 10 equal, 29 differ

Against live AA:
- Their cost appears on some live host row for 139/150 entries.
- The live models-leaderboard `intelligenceIndexCostPerTask` equals their cost for 181/186.

**Conclusion:** same source and different snapshot. For parity, read the model-level cost from the models leaderboard instead of the per-host `costPerTask`.

## 5. Frontier and Notable families (bundle.pretty.js ~28602, `L` and `Rt`)

Frontier (`L`):

| family | tier | ours with cost (efforts) | theirs (efforts) |
|---|---|---|---|
| gpt-6-astra | Large | 5: low…max | same |
| gpt-6-1-sol | Medium | **missing** | low…max (released 2026-09-29) |
| gpt-6-luna | Small | 6: none…max | same |
| claude-opus-5-5 | Large | 5: low…max | same |
| claude-fable-5-1 | Large | 5: low…max | same |
| claude-sonnet-5-5 | Medium | **missing** | low…max (2026-09-28) |
| claude-haiku-5-5 | Small | **missing** | low…max (2026-10-07) |
| gemini-4-argon | Large | **missing** | high (2026-09-30) |
| gemini-3-8-flash | Medium | 2: medium, high (low present without cost) | low (no cost), medium, high |
| grok-4-7 | Large | 2: high, xhigh | low, high, xhigh (low absent from ours) |

Notable (`Rt`): all 7 families have at least one cost entry in ours.

| family | ours with cost | theirs | gap in ours |
|---|---|---|---|
| mimo-v2-6-pro | default | default | none |
| muse-spark-1-3 | xhigh, max | xhigh, max | none |
| kimi-k3 | max | low, max | low present without cost |
| glm-5-3 | max | low, max | low absent |
| glm-5-3-flash | 1 (name rule gives default) | max | effort label only |
| deepseek-v4-pro | max | none, max | non-reasoning absent |
| deepseek-v4-1-flash | max | none, max | non-reasoning absent |

Frontier: 6/10 present, 4 missing. All 4 missing families were released after our snapshot and are in the live providers feed with cost. One more hard-coded set: `zt = {gemini-3-5-flash-lite}` is forced deprecated.

## 6. Provider vs creator

`provider == creator` holds for 113/152 cost entries.

Of the 17 multi-variant families, 16 use one provider for every variant (all first-party). The exception is **qwen3-8-27b**:
- xhigh and non-reasoning → Wafer
- low and medium → Alibaba Cloud, the only host for those two

The cause is our dedup's first-party test, `host.name == creator.name`. It fails for these pairs:
- creator "Alibaba" vs host "Alibaba Cloud" (58 rows live)
- "Z AI" vs "Zai"
- "Amazon" vs "Amazon Bedrock"
- "Microsoft" vs "Microsoft Azure"

When the test fails, the dedup falls back to the cheapest host. The same flaw puts glm-5-3 on Baseten, and glm-5-2 and glm-5-3-flash on Bitdeer AI, while AA's model-level host is Zai.

35 single-variant families have provider ≠ creator, e.g. gpt-oss → CoreWeave, gemma → DeepInfra/Parasail, Qwen open models → various hosts. If subscription-plan pricing is keyed on `provider`, these need either a creator-based key or a fixed host alias map: Alibaba↔Alibaba Cloud, Z AI↔Zai, Amazon↔Amazon Bedrock, Microsoft↔Microsoft Azure.
