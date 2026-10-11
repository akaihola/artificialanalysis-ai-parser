# Artificial Analysis payload facts for the slopalytics chart rebuild

Fetched 2026-10-11 (UTC+3 morning). All findings are from live downloads in
`/tmp/claude-1002/slopalytics-facts/downloads-aa/`. Scripts are in
`/tmp/claude-1002/slopalytics-facts/scripts-aa/`. Nothing in the repo was modified.

## 1. What was fetched

| File | URL | Headers | Size (decompressed) |
|---|---|---|---|
| `providers.rsc` | `https://artificialanalysis.ai/leaderboards/providers?_rsc=hgvan` | identical to `RSC_HEADERS` in `artificialanalysis.ai-parser.py` | 2.77 MB |
| `models.rsc` | `https://artificialanalysis.ai/leaderboards/models?_rsc=hgvan` | identical to `RSC_HEADERS` | 1.18 MB |
| `model-gpt-4-1.rsc` / `.html` | `https://artificialanalysis.ai/models/gpt-4-1?_rsc=hgvan` (and the HTML page) | `rsc: 1`, `next-url: /models/gpt-4-1`, same UA | 3.20 MB / 4.06 MB |
| `model-claude-opus-5-5-xhigh.rsc` / `.html`, `model-gpt-6-1-sol-high.rsc` / `.html` | `/models/<slug>` | as above | 0.75 MB / 1.47 MB each |
| `model-mercury-2.rsc`, `model-gpt-4o.rsc` | `/models/<slug>?_rsc=hgvan` | as above | 3.2 MB each |
| `models-index.rsc` | `/models?_rsc=hgvan` | as above | 0.68 MB |

Fetch script: `scripts-aa/fetch.sh` uses the scraper's headers. `scripts-aa/fetch_pages.sh` fetches the model pages.

## 2. Data blocks inside the scraper's two payloads

Both payloads contain three JSON blocks with per-model data:

1. **Nav props.** The object starts with `{"modelsAndReleases":` and holds the props of the `Nav` component (RSC line `d`). It appears in BOTH payloads.
   - `modelsAndReleases.releases[]` (503 items): `{slug, name, deprecated, releaseDate, creator:{slug, name, logo}}`. A "release" is the base model, or family.
   - `modelsAndReleases.models[]` (697 items): `{slug, name, releaseSlug}`. Here `name` is the full variant name, e.g. `"Claude Opus 5.5 (Xhigh, Default Fallback)"`.
   - The wrapper also contains `hosts`, `sttModelFamilies`, `imageModelFamilies`, `textToSpeechModelFamilies`, `videoModelFamilies`, `locale`, and `messages`.
   - The first `"models":[` that the scraper's `extract_model_indexes()` visits is this nav array. It has no scores, so the scraper ignores it.
2. **`HostLeaderboard` props `rows[]`** in `providers.rsc` (1245 host×model rows). The scraper already parses this array (`extract_rows`).
3. **`ModelLeaderboard` props `models[]`** in `models.rsc`. It is the 2nd `"models":[` array (697 items, one per model variant). The scraper reads only `scicode`, `terminalBench40` and `agenticIndex` from it.

### 2a. Full objects for Claude Opus 5.5 (xhigh)

`modelsAndReleases.models[]`:
```json
{"slug":"claude-opus-5-5-xhigh","name":"Claude Opus 5.5 (Xhigh, Default Fallback)","releaseSlug":"claude-opus-5-5"}
```
`modelsAndReleases.releases[]` entry for that releaseSlug:
```json
{"slug":"claude-opus-5-5","name":"Claude Opus 5.5","deprecated":false,"releaseDate":"2026-09-22",
 "creator":{"slug":"anthropic","name":"Anthropic","logo":"/img/logos/anthropic.svg"}}
```
`rows[]` (providers.rsc, Anthropic host; 1 host row exists):
```json
{"id":"56197281-...","label":"Claude Opus 5.5 (xhigh with fallback)","hostApiId":"claude-opus-5-5","footnotes":null,
 "host":{"name":"Anthropic","slug":"anthropic","logo":"anthropic.svg","color":"#CD9D7B","functionCallingUrl":"...","jsonModeUrl":"..."},
 "model":{"slug":"claude-opus-5-5-xhigh","isOpenWeights":false,"deprecated":false,"reasoningModel":true,
   "intelligenceIndex":55.987,"intelligenceIndexIsEstimated":false,"omniscience":42.65,"omniscienceAccuracy":0.654,
   "omniscienceNonHallucination":0.343,"briefcase":{"elo":1767.57},"harveyLab":null,"automationBench":0.650,
   "gdpvalNormalized":0.669,"terminalbenchHard":null,"terminalBench21":null,"terminalBench40":0.596,"tau2":null,
   "tauBanking":null,"lcr":0.847,"hle":0.575,"gpqa":null,"scicode":0.650,"livecodebench":null,"aime25":null,
   "ifbench":null,"critpt":0.317,"apexAgents":null,"itbenchSre":null,"mmmuPro":0.866,"sizeClass":"large",
   "creator":{"name":"Anthropic","logo":"anthropic.svg"}},
 "features":{"contextWindowTokens":1000000,"functionCalling":true,"jsonMode":false,"openaiCompatible":true},
 "pricing":{"costPerTask":3.459110175822289,"priceClass":"high","price1mInputTokens":4,"price1mOutputTokens":20,
   "cacheHitPrice":0.2,"cacheWritePrice":5},
 "performance":{"medianOutputTokensPerSecond":80.79,"percentile05OutputTokensPerSecond":66.1,"quartile25OutputTokensPerSecond":72.7,
   "quartile75OutputTokensPerSecond":85.5,"percentile95OutputTokensPerSecond":88.5,"medianTimeToFirstTokenSeconds":127.8,
   "percentile05TimeToFirstTokenSeconds":76.2,"quartile25TimeToFirstTokenSeconds":109.4,"quartile75TimeToFirstTokenSeconds":147.9,
   "percentile95TimeToFirstTokenSeconds":183.4,"medianTimeToFirstAnswerTokenSeconds":127.8,
   "medianEndToEndResponseTimeSeconds":134.0,"medianReasoningTimeSeconds":null}}
```
`ModelLeaderboard models[]` (models.rsc) holds the same data in flat form. Keys: `slug, name, shortName, deprecated, isReasoning,
isOpenWeights, paramClass, priceClass, modelCreatorName, modelCreatorColor ("#cc785c"), modelCreatorLogo ("/img/logos/anthropic.svg"),
contextWindowTokens, intelligenceIndex, intelligenceIndexIsEstimated, omniscience, omniscienceAccuracy, omniscienceNonHallucination,
gdpvalNormalized, analystAgent, terminalbenchHard, terminalBench21, terminalBench40, tau2, tauBanking, lcr, hle, gpqa, scicode,
ifbench, critpt, apexAgents, itbenchSre, mmmuPro, intelligenceIndexCostPerTask (number: 3.459110175822289), price1mInputTokens,
price1mOutputTokens, cacheHitPrice, cacheWritePrice`. It also has the same 13 `performance` keys as `rows[]`, at top level.

GPT-6.1 Sol (high) has the same shape: nav `name` = `"GPT-6.1 Sol (High)"`, `releaseSlug` = `"gpt-6-1-sol"`, release
`releaseDate` = `"2026-09-29"`, creator `openai`/`OpenAI`/`/img/logos/openai.svg`. `rows[].hostApiId` = `"gpt-6.1-sol"`,
`label` = `"GPT-6.1 Sol (high)"`, `pricing.costPerTask` = 0.31914442375664703. Full dumps are in
`scripts-aa/sample-models.txt`.

## 3. Requested fields: present in OUR payloads?

The key paths below are relative to the blocks in section 2. "nav" = `modelsAndReleases`.

| Requested field | In our payloads? | Exact key path(s) |
|---|---|---|
| Model family / base model id | **YES** | `nav.models[i].releaseSlug` (join on `slug` = row `model.slug`). Family display name: `nav.releases[j].name` where `releases[j].slug == releaseSlug`. All 697 models resolve to one of 503 releases. Matches the AA model page `release.slug` 697/697. |
| Reasoning effort level / variant label | **PARTIAL (string only)** | No structured effort field. The effort appears only in display strings: `nav.models[i].name` ("…(Xhigh, Default Fallback)"), `ModelLeaderboard models[i].shortName` and `rows[i].label` ("…(xhigh with fallback)"), plus the slug suffix (`-xhigh`). Parsing the trailing parenthetical for {minimal, low, medium, high, xhigh, max} reproduces AA's structured `effort.slug` for **681/697** models. The 16 misses are single-variant reasoning models that AA tags with an effort but whose names lack one (mercury-2, gemini-3-5-flash-lite, glm-5-3-flash = max, solar-pro-3, step-3-7-flash, k2-think-v2, …), and the "(Non-reasoning, High)" Claude names, where AA's effort is null. The numeric order (`effortOrder`) is not in our payloads; see section 4. |
| Release date | **YES** | `nav.releases[j].releaseDate` ("YYYY-MM-DD"), via `releaseSlug`. Present for all 503 releases. Matches the model page `releaseDate` 697/697. Release-level `deprecated` is also available. |
| Lab/creator display name | **YES** | `rows[i].model.creator.name` (already used); `ModelLeaderboard models[i].modelCreatorName`; `nav.releases[j].creator.name`. Lab slug: only `nav.releases[j].creator.slug`, since rows have no creator slug. |
| Lab logo URL | **YES** | `rows[i].model.creator.logo` = bare filename "anthropic.svg"; `ModelLeaderboard models[i].modelCreatorLogo` and `nav.releases[j].creator.logo` = "/img/logos/anthropic.svg". Absolute: `https://artificialanalysis.ai/img/logos/<file>` (verified HTTP 200 image/svg+xml). Lab colour: `models[i].modelCreatorColor`. Host logo/colour: `rows[i].host.logo` / `.color`. |
| Tokens used per task | **NO** | Not present (0 occurrences of `outputTokensPerTask` / `intelligenceIndexOutputTokensPerTask` in either payload). |
| Tokens for the whole Intelligence Index run | **NO** | Not present (`canonicalIntelligenceIndexTokenCount` absent). |
| Time per task / time to run the index | **NO** | Not present (`intelligenceIndexTimePerTask`, `timePerTask` absent). `medianEndToEndResponseTimeSeconds` is per-request latency on AA's standard prompt (134 s for Opus 5.5 xhigh), not index time per task (494 s). It is not a substitute. |
| Total cost to run the index | **NO** | Not present (`intelligenceIndexCost` object absent). Only per-task cost exists: `rows[i].pricing.costPerTask` and `ModelLeaderboard models[i].intelligenceIndexCostPerTask`. These equal the page's `intelligenceIndexCostPerTask.cost.total` for 691/697. The total cannot be derived: costTotal/costPerTask ranges from 804 to 3805 across models, and tokensTotal/tokensPerTask from 1196 to 6617, because per-task values are weighted means over evaluations. |
| Open-weights flag | **YES** (already extracted) | `rows[i].model.isOpenWeights`; `models[i].isOpenWeights`. |
| Deprecated flag | **YES** (already extracted) | `rows[i].model.deprecated`; `models[i].deprecated`; release level: `nav.releases[j].deprecated`. |
| (bonus) Intelligence-estimated flag | YES, not extracted | `rows[i].model.intelligenceIndexIsEstimated`; `models[i].intelligenceIndexIsEstimated`. |

## 4. Where slopalytics' data comes from: AA model pages

Slopalytics' `models.json` metadata says `source: https://artificialanalysis.ai/models/gpt-4-1`. That is correct.

- On a model page for a model **without** effort variants, the page renders `LanguageModelCompareButton`. Examples are `/models/gpt-4-1`, `/models/gpt-4o` and `/models/mercury-2`. Its props are `{currentModel, models, messages}`, and `props.models` holds **all 697 model variants** as full objects. One entry is replaced by the string reference `"$e:props:…:currentModel"`, and that model's object sits in `props.currentModel`. The RSC path in `model-gpt-4-1.rsc` is line `e` → `[3].children[0][3].children[3].children[1][3].children[1][3].children[0][3].models`. In practice, find the `"models":[{` array whose items have `intelligenceIndexEvaluations`.
- On a model page **with** variants, the page renders `LanguageModelVariantSelector` instead. Examples are `/models/claude-opus-5-5-xhigh` and `/models/gpt-6-1-sol-high`. Its props are `{releaseName, releaseSlug, selected:{label,href}, options:[{label:"max",href:"/models/claude-opus-5-5"},…]}`. These pages carry only `initialModels` with 26 full objects (a comparison set), not the full list. `/models` (index) also has only ~25 full objects.
- URL pattern: `https://artificialanalysis.ai/models/<slug>?_rsc=<any>` with headers `rsc: 1`, `next-url: /models/<slug>` and a UA. `next-router-state-tree` is not needed. The response is 200 and about 3.2 MB decompressed (~525 kB gzip). The HTML page embeds the same data inside `self.__next_f.push` strings.

### Full model-page object keys

Example: `claude-opus-5-5-xhigh`, from `scripts-aa/page-opus-xhigh.json`.

`id, slug, name, shortName, suffix ("Xhigh, Default Fallback"), chartDefaultSelected, chartHighlighted, releaseDate,
knowledgeCutoffDate, isReasoning, reasoningTokens, effort{slug,label,level}, release{slug,name,deprecatedTo}, deprecated,
isOpenWeights, openSourceCategorization, parameters, inferenceParametersActiveBillions, sizeClass, contextWindowTokens,
licenseName, licenseUrl, modelWeightsSourceUrl, microevalsEnabled, intelligenceIndex, intelligenceIndexIsEstimated,
capabilities{financeAndAccounting,strategyAndOps,legal,engineering,economics}, omniscience, omniscienceAccuracy,
omniscienceHallucinationRate, gdpPdfAllPass, gdpval, gdpvalNormalized, itBenchSre, tau2, tauBanking, terminalbenchHard,
terminalBench21, terminalBench40, frontierCode, terminalBenchScience, hleDiamond, scicode, lcr, ifbench, hle, gpqa, critpt,
apexAgents, mmmuPro, livecodebench, aime25, analystAgent, automationBenchPartialScore, price1mInputTokens, price1mOutputTokens,
cacheHitPrice, cacheHitDiscountPercent, cacheWritePrice, pricePer1k1mpImages, price1mBlended{0To3To1,7To2To1,0To1To1,100To1To1,0To100To1},
intelligenceIndexTimePerTask, intelligenceIndexCost{total,input,nonCacheInput,cacheRead,cacheWrite,output,reasoning,answer},
intelligenceIndexCostPerTask{cost{same 8 keys}, evaluations[{slug,weightedCostPerTask}]},
canonicalIntelligenceIndexTokenCount{input,output,answer,reasoning}, intelligenceIndexOutputTokensPerTask{reasoning,answer,output},
intelligenceIndexEvaluations[{slug,score,outputTokensPerTask,costPerTask,timePerTask}] (10 evals),
briefcaseBreakdown{overall,rubricPassRate,analyticalQuality,presentation}, briefcaseTotalCost,
timescaleData{medianOutputSpeed,medianTimeToFirstChunk}, outputSpeedVariance{p05,q25,median,q75,p95}, timeToFirstChunkVariance{…},
performanceByPromptType{medium,long,hundredK,mediumParallel}{medianOutputSpeed,medianTimeToFirstChunk,medianTimeToFirstAnswerToken,medianEndToEndResponseTime},
endToEndResponseTime{input,reasoning,answer,total}, timeToFirstAnswerToken{input,reasoning,total},
performanceDataSource{type:"firstParty"|"median",providerName}, hostModelCount, creator{id,slug,name,logo,color,country},
input/outputModality{Text,Image,Speech,Video}`.

### Slopalytics field → AA model-page key

Verified by joining all 696 slopalytics records to `/models/gpt-4-1` `props.models` (`scripts-aa/compare.py`).

| slopalytics | AA model-page key | exact match | in our payloads? |
|---|---|---|---|
| `id` | `slug` | 696/696 joined | yes |
| `family` | `release.slug` | 696/696 | yes: `nav.models[].releaseSlug` |
| `name` | `release.name` | 695/696 | yes: `nav.releases[].name` |
| `variant` | `shortName` | 696/696 | yes: `models[].shortName` / `rows[].label` |
| `lab` / `labName` | `creator.slug` / `creator.name` | 696/696 | yes (slug only via `nav.releases[].creator.slug`) |
| `released` | `releaseDate` | 696/696 | yes: `nav.releases[].releaseDate` |
| `open` | `isOpenWeights` | 696/696 | yes |
| `deprecated` | `deprecated` | 694/696 (drift) | yes |
| `effort` / `effortLabel` / `effortOrder` | `effort.slug` / `effort.label` / `effort.level` when `effort` is non-null (182/182 exact). When `effort` is null, slopalytics synthesizes values: `isReasoning` → `"default"/"Default"/35` (220 models), else `"none"/"Non-reasoning"/0` (294 models). AA level scale: minimal 10, low 20, medium 30, high 40, xhigh 50, max 60. | 696/696 with that rule | partial: parse from names (681/697), hard-code the level scale |
| `estimated` | `intelligenceIndexIsEstimated` | 695/696 | yes |
| `intelligence` | `intelligenceIndex` | 694/696 | yes (already) |
| `cost` | `intelligenceIndexCostPerTask.cost.total` | 685/696 (175/185 non-null) | yes: `pricing.costPerTask` / `models[].intelligenceIndexCostPerTask` |
| `costTotal` | `intelligenceIndexCost.total` ("USD, full index run") | 685/696 | **NO** |
| `tokens` | `intelligenceIndexOutputTokensPerTask.output` (output tokens per task) | 691/696 (198/202 non-null) | **NO** |
| `tokensTotal` | `canonicalIntelligenceIndexTokenCount.output` ("output tokens, full index run") | 691/696 | **NO** |
| `time` | `intelligenceIndexTimePerTask` (seconds, "Time per task") | 0 exact; null pattern consistent (177 vs 184 now); values drift daily (median 6.5% off after 3 days) | **NO** |
| `speed` | Ambiguous. Page `timescaleData.medianOutputSpeed` (= `outputSpeedVariance.median`) is the likely source, but its null pattern now differs by 28 DeepSeek models. Our `medianOutputTokensPerSecond` has an identical null pattern (354/354) and a 3% median deviation. Values drift daily, so neither matches exactly. | 0 exact | approximately yes (already extracted) |
| `inputPrice` / `outputPrice` / `context` | `price1mInputTokens` / `price1mOutputTokens` / `contextWindowTokens` | 688, 686, 696 | yes (already) |

Spot checks for exact matches:
- Opus 5.5 xhigh: `tokens` 65667.3950659979, `tokensTotal` 99668308, `costTotal` 4056.6546786492113, `cost` 3.459110175822289.
- GPT-6.1 Sol high: `tokens` 13191.870219821281, `tokensTotal` 25376903, `costTotal` 521.3175499431111.

## 5. Not available from our current payloads

These require fetching an AA model page as in section 4:

- Tokens per task (`intelligenceIndexOutputTokensPerTask.*`)
- Total index tokens (`canonicalIntelligenceIndexTokenCount.*`)
- Time per task (`intelligenceIndexTimePerTask`, per-eval `timePerTask`)
- Total index cost (`intelligenceIndexCost.*`)
- Structured reasoning effort and its numeric order (`effort{slug,label,level}`)
- Lab country (`creator.country`). Lab colour is available as `modelCreatorColor`.
- Knowledge cutoff, parameter counts, licence, modalities
- Per-evaluation breakdowns and blended price variants

Effort can be approximated from name strings (681/697 correct). Family, release date, lab name/slug/logo, open weights and deprecated ARE available.

## 6. Fields in our payloads that the scraper does not extract yet

- `rows[]`:
  - Endpoint and host: `id` (endpoint UUID), `hostApiId` (API model string, e.g. `gpt-6.1-sol`), `footnotes`, `host.slug/logo/color/functionCallingUrl/jsonModeUrl`
  - Model and creator: `model.intelligenceIndexIsEstimated`, `model.sizeClass`, `model.creator.logo`
  - Benchmarks: `model.omniscience*`, `model.briefcase.elo`, `model.harveyLab`, `model.automationBench`, `model.gdpvalNormalized`, `model.terminalbenchHard/terminalBench21`, `model.tau2/tauBanking`, `model.lcr`, `model.livecodebench`, `model.ifbench`, `model.critpt`, `model.apexAgents`, `model.itbenchSre`, `model.mmmuPro`
  - Features: `features.functionCalling/jsonMode/openaiCompatible`
  - Pricing: `pricing.priceClass`, `pricing.cacheWritePrice`
  - Performance: `performance.medianTimeToFirstAnswerTokenSeconds`, `performance.medianReasoningTimeSeconds`, and the p05/q25/q75/p95 values for output speed and TTFT
- `ModelLeaderboard models[]`:
  - Names and creator: `name`, `shortName`, `modelCreatorName/Color/Logo`
  - Classification: `isReasoning`, `paramClass`, `priceClass`
  - Index data: `intelligenceIndexIsEstimated`, `intelligenceIndexCostPerTask`, `analystAgent`, plus the benchmarks listed for `rows[]`
  - Per-variant performance, covering all 697 variants including unpriced ones, which `rows` only has per host
- nav: `releaseSlug` (family), release `name`, `releaseDate`, release `deprecated`, and `creator.slug/name/logo`.

## 7. Side findings

- `agenticIndex` no longer exists anywhere in `models.rsc` (0 occurrences). `agentic_index` is therefore null for all 426 models in the repo's current `models.json`.
- `models.rsc` and `providers.rsc` contain identical nav blocks, so `models.rsc` alone covers family, release date and lab slug.
- `gpt-6-sol-daybreak-blue` (name "GPT-6 Sol (Daybreak Blue, max)", AA effort `max`) is new since slopalytics' snapshot (2026-10-08). Slopalytics has 696 models; AA now has 697.

## 8. Scripts

- `scripts-aa/fetch.sh`, `scripts-aa/fetch_pages.sh`: downloads.
- `scripts-aa/inspect.py`: key-path census of `rows`/`models` arrays (output in `keys.txt`).
- `scripts-aa/releases.py`: nav `modelsAndReleases` shape.
- `scripts-aa/dump_model.py`: dumps all payload objects for a slug (output in `sample-models.txt`).
- `scripts-aa/find_arrays.py`, `model_page.py`, `dump_page_model.py`: locate and dump model-page objects (`page-opus-xhigh.json`, `page-gpt61-high.json`).
- `scripts-aa/compare.py`, `derive_check.py`, `speed_check.py`: slopalytics↔AA mapping verification and derivability checks.
