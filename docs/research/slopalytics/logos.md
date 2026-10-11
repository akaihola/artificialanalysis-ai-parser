# Lab logos: slopalytics origin, coverage for our creators, inlining cost, licensing

Date: 2026-10-11. Packages checked: `@lobehub/icons-static-svg` 1.95.1 (MIT, 950 SVGs), `simple-icons` 16.34.0 (CC0-1.0, 3464 icons). Also checked `pheralb/svgl` (GitHub `main` tarball, MIT repo, 1103 SVGs) and `@iconify-json/logos` 1.2.15 / `@iconify-json/simple-icons` 1.2.99, because the first two packages did not explain most of the slopalytics files.

## 1. Slopalytics embedded logos and where they come from

How they are used (bundle.pretty.js):
- Lines ~29203-29247: nine SVG strings `An…Rn` turned into `data:image/svg+xml;charset=utf-8,${encodeURIComponent(svg)}` URIs (map `Vn`, lookup `Hn(lab)`).
- `Bn = new Set(["openai","anthropic","xai","kimi","zai"])` adds the `monochrome-logo` class. CSS: `.monochrome-logo{filter:var(--logo-filter)}`, `--logo-filter: none` by default (dark theme) and `invert(1)` under the light color scheme (style.pretty.css lines 760, 777, 2049). These five SVGs are white-filled, drawn for a dark background.
- Component `Un` (line ~29253) renders `<img class="lab-logo [monochrome-logo]" width=18 height=18 alt="" aria-hidden>`. With no logo it renders `<span class="lab-logo lab-monogram">` holding the first character of the lab name, `font-size = size*0.55`, background `var(--hover)`, colour `var(--fg-2)`, radius 3px, weight 600 (CSS 1385-1400).
- Chart direct labels (line ~30417) use SVG `<image href=dataURI x=27 y=-9 width=18 height=18>`. When a logo exists, the label text moves from x=27 to x=53. Sidebar rows dim the logo to `opacity:.4` and restore 1 on hover or when pressed (CSS 1342-1348).

Embedded set and its sources. "Byte-identical" means `cmp` shows the files are identical. Extracted copies are in `downloads-logos/slopalytics-embedded/`.

| slopalytics key | lab (their data) | bytes | inverted in light | direct source | upstream / notes |
|---|---|---|---|---|---|
| openai | OpenAI | 2430 | yes | svgl `openai_dark.svg` (byte-identical) | OpenAI "blossom" mark, viewBox 611x611, white fill. Not in lobehub (lobehub `openai.svg` is a different, older path). Absent from simple-icons. |
| anthropic | Anthropic | 348 | yes | svgl `anthropic_white.svg` (byte-identical) | Same path as lobehub `anthropic.svg` (identical `d`), with lobehub's `style="flex:none;line-height:1"` and `width="1em"` and `fill="#ffff"`. svgl copied it from lobehub. |
| google | Google | 8169 | no | svgl `google.svg` (byte-identical) | 2025 gradient "G" (viewBox 0 0 268.152 273.883). Not in lobehub or simple-icons. |
| xai | SpaceXAI | 317 | yes | svgl `xai_dark.svg`, hand-edited | Same path. The viewBox was cropped from `0 0 841.89 595.28` to `201.61 56.91 438.67 481.45` (tight bbox). Geometrically the same mark as lobehub `xai.svg`, but different coordinates. |
| meta | Meta | 2199 | no | svgl `meta.svg` (byte-identical) | Gradient infinity mark. Same first-40-char paths as gilbarbara `logos:meta-icon` (via @iconify-json/logos), so it is a gilbarbara-style asset. |
| kimi | Kimi | 957 | yes | svgl `kimi-icon.svg` (byte-identical) | Black rounded square, white K, blue (#027aff) dot. Under the light-theme invert the dot turns orange. |
| zai | Z AI | 230 | yes | lobehub `zai.svg` (path `d` byte-identical) | Attributes rewritten: `fill="#fff"`, title, style, width and height dropped. Not in svgl. |
| deepseek | DeepSeek | 2126 | no | svgl `deepseek.svg` (byte-identical) | Derived from lobehub `deepseek-color.svg` (#4D6BFE, lobehub `style` attr kept). Arc flags are expanded (`0 0 1` vs `01`). 72 of 73 normalised segments are identical; one tiny segment is an arc in svgl and a cubic in current lobehub, so svgl probably copied an older lobehub revision. |
| xiaomi | Xiaomi | 883 | no | Iconify `simple-icons:xiaomi` | Path `d` is byte-identical to the @iconify-json/simple-icons body, and geometrically identical to simple-icons `xiaomi.svg` apart from Z/closing. `fill="currentColor"` was replaced by simple-icons' brand hex `#ff6900`. Iconify markup (`width="1em" height="1em"`). |

Conclusion: 7 of the 9 come straight from svgl (svgl.app). Of those, Anthropic and DeepSeek are svgl copies of lobehub art. Z.ai is lobehub with rewritten attributes, and Xiaomi is simple-icons via Iconify. Only Anthropic and Z.ai have byte-identical paths in lobehub 1.95.1. Total embedded payload is 17,659 B raw and 23,488 B as encodeURIComponent data-URIs.

## 2. Coverage for creators in our models.json (39 creators, 426 models)

Lobehub naming: the base `<slug>.svg` is mono (`fill="currentColor"`, viewBox 0 0 24 24, about 300 B of wrapper). `<slug>-color.svg` is the colour variant, and gradient colour files carry ids like `lobe-icons-qwen-_R_0_`. `-text` files are wordmarks and `-brand` files are combined marks. Simple-icons ships mono only: one `<path>` with no fill attribute (renders black), plus a brand `hex` in `data/simple-icons.json`.

| Creator | models | lobehub mono | lobehub color | other lobehub options | simple-icons (slug, hex, bytes) |
|---|---|---|---|---|---|
| OpenAI | 94 | `openai.svg` (1687 B) | - |  | - (no OpenAI icon) |
| Alibaba | 65 | `alibaba.svg` (1412 B) | `alibaba-color.svg` (1407 B) | `qwen`, `qwen-color`, `alibabacloud` | `alibabacloud` (#FF6A00, 547 B); `alibabadotcom` (#FF6A00, 946 B); `qwen` (#6950EF, 805 B) |
| Anthropic | 45 | `anthropic.svg` (368 B) | - | `claude`, `claude-color` | `anthropic` (#191919, 281 B); `claude` (#D97757, 1921 B) |
| Google | 33 | `google.svg` (900 B) | `google-color.svg` (920 B) | `gemini`, `gemini-color`, `deepmind`, `deepmind-color` | `google` (#4285F4, 457 B, guidelines URL); `googlegemini` (#8E75B2, 401 B); `deepmind` (#4285F4, 726 B) |
| DeepSeek | 23 | `deepseek.svg` (2189 B) | `deepseek-color.svg` (2164 B) |  | `deepseek` (#5786FE, 2086 B) |
| SpaceXAI | 21 | `xai.svg` (372 B; title says "Grok" but it is the xAI mark) | - | `grok` | `spacex` (#000000, 323 B; SpaceX swoosh, not xAI) |
| Z AI | 19 | `zai.svg` (319 B) | - | `zhipu`, `zhipu-color`, `chatglm`, `chatglm-color` | `zdotai` (#2D2D2D, 343 B) |
| Mistral | 16 | `mistral.svg` (418 B) | `mistral-color.svg` (655 B) |  | `mistralai` (#FA520F, 290 B) |
| Meta | 14 | `meta.svg` (1735 B) | `meta-color.svg` (6022 B) | `meta-brand(-color)`, `metaai(-color)` | `meta` (#0467DF, 1324 B, guidelines URL); `metaai` (#9844FF, 1042 B) |
| Amazon | 13 | `aws.svg` (3234 B, "aws" smile wordmark) | `aws-color.svg` (3242 B) | `nova`, `nova-color`, `bedrock(-color)` | - |
| Kimi | 10 | `kimi.svg` (786 B) | `kimi-color.svg` (773 B; white K, needs a dark background) | `moonshot` | `kimi` (#000000, 654 B, guidelines URL); `moonshotai` (#000000, 652 B) |
| NVIDIA | 9 | `nvidia.svg` (1030 B) | `nvidia-color.svg` (1025 B) |  | `nvidia` (#76B900, 881 B) |
| InclusionAI | 7 | `antgroup.svg` (1337 B; parent Ant Group, proxy) | `antgroup-color.svg` (2460 B) | `antgroup-brand(-color)` | - |
| MiniMax | 6 | `minimax.svg` (1334 B) | `minimax-color.svg` (1570 B) |  | `minimax` (#E73562, 721 B, license: custom) |
| IBM | 6 | `ibm.svg` (1651 B, striped wordmark) | - |  | - |
| Xiaomi | 5 | `xiaomimimo.svg` (2544 B, "Xiaomi MiMo" wordmark, unreadable at 18px) | - |  | `xiaomi` (#FF6900, 903 B), better at 18px |
| StepFun | 4 | `stepfun.svg` (447 B) | `stepfun-color.svg` (676 B) |  | - |
| Sapiens AI | 3 | - | - |  | - |
| Upstage | 3 | `upstage.svg` (898 B) | `upstage-color.svg` (946 B) |  | - |
| Tencent | 3 | `tencent.svg` (282 B) | `tencent-color.svg` (277 B) | `hunyuan(-color)`, `tencentcloud(-color)` | `tencenthy` (#0052D9, 645 B; Hunyuan mark) |
| Nous Research | 3 | `nousresearch.svg` (19786 B, outlier) | - |  | - |
| Thinking Machines | 2 | - | - |  | - |
| Inception | 2 | `inception.svg` (309 B) | - |  | - |
| Sarvam | 2 | - | - |  | - |
| Reka AI | 2 | `reka.svg` (2866 B) | - |  | - |
| AI21 Labs | 2 | `ai21.svg` (1235 B) | - (only `ai21-brand-color`, 3847 B) | `ai21-brand(-color)` | - |
| Swiss AI Initiative | 2 | - | - |  | - |
| Apodex | 1 | - | - |  | - |
| Multiverse Computing | 1 | - | - |  | - |
| KwaiKAT | 1 | `kwaikat.svg` (608 B) | - (`kwaikat-text-color` is a wordmark) | `kwaipilot(-color)` | `kuaishou` (#FF4906, 1165 B, guidelines URL; parent) |
| LongCat | 1 | `longcat.svg` (804 B) | `longcat-color.svg` (819 B) |  | `meituan` (#FFD100, 1200 B; parent) |
| ByteDance Seed | 1 | `bytedance.svg` (873 B) | `bytedance-color.svg` (953 B) | `doubao(-color)` | `bytedance` (#3C8CFF, 331 B) |
| Arcee AI | 1 | `arcee.svg` (402 B) | `arcee-color.svg` (377 B) |  | - |
| Baidu | 1 | `baidu.svg` (1389 B) | `baidu-color.svg` (1384 B) | `wenxin(-color)` | `baidu` (#2932E1, 1391 B) |
| Cohere | 1 | `cohere.svg` (724 B) | `cohere-color.svg` (769 B) |  | - |
| Celeris | 1 | - | - |  | - |
| Microsoft | 1 | `microsoft.svg` (379 B; four squares, title says "Azure") | `microsoft-color.svg` (399 B) | `azure(-color)` | - |
| Allen Institute for AI | 1 | `ai2.svg` (600 B) | `ai2-color.svg` (575 B) |  | - |
| Deep Cogito | 1 | `deepcogito.svg` (1695 B) | `deepcogito-color.svg` (1670 B) |  | - |

Counts:
- lobehub has a mono icon for 32 of 39 creators, 414 of 426 models counting the parent-brand proxies (antgroup for InclusionAI). A colour variant exists for 21 of those 32.
- No colour variant: OpenAI, Anthropic, SpaceXAI, Z AI, IBM, Xiaomi, Nous, Inception, Reka, AI21 (mark), KwaiKAT.
- simple-icons covers 17 creators (Anthropic, Google, DeepSeek, Z AI, Mistral, Meta, Kimi, NVIDIA, MiniMax, Xiaomi, Tencent, ByteDance, Baidu, Alibaba via alibabacloud/qwen), plus 3 only through parent or proxy (SpaceX, Kuaishou, Meituan).
- simple-icons 16.34.0 has no OpenAI, IBM, Amazon/AWS, Microsoft, Cohere or xAI.
- Neither package has Sapiens AI, Thinking Machines, Sarvam, Swiss AI Initiative, Apodex, Multiverse Computing or Celeris (7 creators, 12 models). svgl does not have them either. Use the monogram fallback.
- For Alibaba, AA's Alibaba models are Qwen, so `qwen.svg` (lobehub) or `qwen` (simple-icons) may read better than the Alibaba script logo. Slopalytics uses a monogram for Alibaba.

Visual check: `scripts-logos/out/contact.png` (rendered contact sheet of every candidate, on light and inverted dark). All picks are the expected brand marks.

## 3. Inlining cost (mono, one hidden `<svg>` sprite of `<symbol>`s, used via `<use href="#id">`)

Each symbol is the lobehub or simple-icons inner markup, with title, style, width, height and `fill="currentColor"` stripped and the viewBox kept. With `fill: currentColor` on the `<use>`, theming is automatic and no invert filter is needed.

| set | icons | raw bytes | gzip -9 |
|---|---|---|---|
| lobehub mono, every covered creator (`sprite-lobehub-mono.svg`) | 32 | 50,072 | 21,714 |
| Recommended picks (lobehub, but simple-icons `xiaomi` for Xiaomi) | 32 | 48,523 | 21,088 |
| Same, without Nous Research (19,635 B alone) | 31 | 28,888 | 12,638 |
| Creators with 5 or more models only | 16 | 17,578 | 7,762 |
| Slopalytics' 9 labs, as our mono equivalents | 9 | 8,141 | 3,788 |
| simple-icons first match for each covered creator | 17 | 12,809 | 5,614 |
| Recommended picks, path numbers rounded to 2 dp (estimate) | 32 | 40,195 | 16,095 |
| Recommended picks, rounded to 1 dp (estimate, not visually verified) | 32 | 30,105 | 10,565 |
| Same without Nous, 1 dp (estimate) | 31 | 19,360 | 7,346 |
| Raw lobehub mono files as shipped | 32 | 54,613 | - |
| The same files as encodeURIComponent data-URIs | 32 | 64,067 | - |
| The same files as minimal-escape data-URIs | 32 | 56,205 | - |
| Slopalytics' 9 actual embedded SVGs, raw / as their data-URIs | 9 | 17,659 / 23,488 | - |

Per-symbol bytes (recommended picks): Nous 19635, Amazon 3089, Reka 2727, DeepSeek 2050, Meta 1596, Deep Cogito 1555, OpenAI 1548, IBM 1512, Alibaba 1273, Baidu 1250, InclusionAI 1198, MiniMax 1195, AI21 1096, NVIDIA 891, Xiaomi(si) 856, Google 743, ByteDance 716, Upstage 700, LongCat 659, Kimi 641, Cohere 573, KwaiKAT 463, Ai2 461, StepFun 308, Mistral 279, Arcee 263, SpaceXAI 232, Anthropic 229, Microsoft 226, Z AI 179, Inception 170, Tencent 143.

For scale, the current `intelligence-vs-cost.html` is 43,169 B. The full lobehub set would roughly double it; leaving out Nous costs about +29 KB raw (about 12.6 KB gzipped).

## 4. License, trademark and attribution requirements

- **@lobehub/icons-static-svg**: `package.json` says `"license": "MIT"`, author "LobeHub <i@lobehub.com>". The npm tarball ships only `icons/` and README, with **no LICENSE file**. The repo LICENSE (github.com/lobehub/lobe-icons) is standard MIT, "Copyright (c) 2023 LobeHub", so if we copy substantial portions we must keep the copyright and permission notice (for example an HTML comment or a THIRD-PARTY notice). Neither the README nor the LICENSE has any trademark disclaimer or brand-usage guidance.
- **simple-icons**: the package is CC0-1.0, so no attribution is required. CC0 §4(a): "No trademark or patent rights held by Affirmer are waived, abandoned, surrendered, licensed or otherwise affected". The README asks users to read DISCLAIMER.md. That file says CC0 does not mean every icon is CC0. Users should check each icon's `license` and `guidelines` in `data/simple-icons.json`, follow brand guidelines, and "seek the correct permissions to use the icons relevant to their project". Simple Icons "cannot be held responsible for any legal activity raised by a brand".
  - Of the icons relevant to us, only `minimax` has license data: `custom`, pointing to a 2025-11-14 PR comment by MiniMax-AI-Dev. It confirms the logo follows MiniMax's design guidelines, "does not constitute any waiver of MiniMax's rights … trademark", and refers to MiniMax's terms of service.
  - Guidelines URLs are given for google (about.google brand-resource-center), meta (facebook.com/brand/resources/meta/company-brand), kimi (moonshotai.github.io/Branding-Guide) and kuaishou.
- **svgl** (the real source of most slopalytics logos): the repo is MIT, "Copyright (c) 2022 Pablo Hdez", which covers the code. The README tells contributors to "ensure you have the right to use it" before adding an SVG. There is no per-logo license. Metadata `brandUrl` gives openai.com/brand and about.meta.com/brand/resources.
- In general, every one of these marks is a third-party trademark whatever the file's copyright license. Showing a lab's logo next to its own models (nominative use) is the normal pattern, but none of the packages grants trademark rights.

## Files

- Report: /tmp/claude-1002/slopalytics-facts/logos.md
- Downloads: /tmp/claude-1002/slopalytics-facts/downloads-logos/
  - `lobehub/package/icons/`, `simple-icons/package/{icons,data,DISCLAIMER.md,LICENSE.md}`
  - `svgl/svgl-main/static/library/` and `svgl/svgl-main/src/data/svgs.ts`
  - `iconify-logos/`, `iconify-si/`
  - `lobe-icons-repo/{LICENSE,README.md}`, `gh/minimax-comment.json`
  - `slopalytics-embedded/*.svg` (the 9 extracted logos)
- Scripts: /tmp/claude-1002/slopalytics-facts/scripts-logos/
  - `extract_embedded.py`, `compare.py` (path match), `geom2.py` and `geomdiff.py` (svgelements geometry compare)
  - `sizes.py` (mapping and totals), `sizes2.py` (per-symbol sizes and subsets), `contact.py` (contact sheet)
  - `out/rows.json`, `out/sprite-lobehub-mono.svg`, `out/contact.png`
