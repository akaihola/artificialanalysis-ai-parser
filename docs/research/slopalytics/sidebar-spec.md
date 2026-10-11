# Slopalytics app shell and model sidebar: implementation spec

Sources (untrusted research artifacts, read only):

- `/tmp/claude-1002/slopalytics-research/bundle.pretty.js`: app component `mr()` at lines 31031-31619; sidebar constants and helpers at 28602-28820 (`L`, `Rt`, `zt`, `Bt`, `Ut`, `Ht`, `Vt`, `Kt`, `qt`, `Yt`, `Xt`); chart list and URL state at 29077-29196 (`gn`, `bn`, `xn`, `Tn`, `On`, `kn`); list derivation at 30919-30930 (`nr`, `rr`, `ar`, `or`, `sr`, `cr`, `ur`, `dr`); settings controls `pr` at 30943-30997; context menu `tr` at 30854-30918; PNG export `er` at 30796-30853; nuqs 2.10.1 internals at 10687-10790 and 11576-11890; lab logos `Un` at 29236-29262.
- `/tmp/claude-1002/slopalytics-research/style.pretty.css` (the only stylesheet; 2050 lines).
- Screenshots `01_viewport.png` (1440x900), `02b_sidebar_default.png`, `13_show_all_models.png`, `15_context_menu.png`, `16_settings_popover.png`, `20_mobile_viewport.png` and `23_mobile_models_sheet.png` (390 px wide at DPR 2), plus `interact_log.json` and `mobile_log.json`, which record observed URLs and text.
- The dataset check script is `/tmp/claude-1002/slopalytics-facts/scripts-sidebar/check_sidebar.py`. Run it with `python3 -I`, passing `models.json` as the argument.

The source is React 19 with nuqs 2.10.1 and lucide icons. The app uses no CSS transitions or animations; the only motion is smooth `scrollIntoView` on a tab click.

---

## 1. Page skeleton and DOM order

```
html[lang=en][data-theme=dark]
  head: meta charset, viewport "width=device-width,initial-scale=1",
        meta theme-color "#000000", meta description, favicon.svg, title "Slopalytics"
  div.app
    header.app-header
      a.brand  > strong > span"slop" + "alytics"
      nav.section-tabs  (Benchmarks | Usage)         -- probably drop in our rebuild
      nav.view-tabs     (chart tabs, divider after 2nd)
      div.header-actions
        button.icon-button             theme toggle
        button.icon-button.desktop-only  PNG download
        details.chart-settings.desktop-only > summary + div.settings-popover
        button.mobile-only.mobile-filter-toggle   "Models N"
    div.body-layout
      main
        div.chart-feed  > section.chart-section#<chartId> (one per chart)
        footer
      aside.sidebar[.open]
    div.context-menu (portal-like, position:fixed, only while open)
```

Static HTML has an empty `#root`. The theme comes from React state, and `data-theme` is set in a layout effect (see section 11).

## 2. Design tokens (CSS variables)

The source CSS is lightningcss output of `light-dark()`. Its raw form uses the `--lightningcss-light/dark` space toggle. In vanilla code we can use native `light-dark()`: the per-model colours already depend on it, and modern browsers support it.

| var | dark (default) | light |
|---|---|---|
| `--bg` | `#000` | `#fff` |
| `--fg` | `#fff` | `#20201e` |
| `--fg-2` | `#aaa39d` | `#625d57` |
| `--fg-3` | `#77716c` | `#77716c` (same) |
| `--line` | `#1c1a18` | `#e8e4df` |
| `--line-2` | `#36312d` | `#ccc5be` |
| `--surface` | `#0d0b0a` | `#f8f6f3` |
| `--hover` | `#141210` | `#f1eeea` |
| `--accent` | `#c5ac98` | `#806047` |
| `--on-accent` | `#000` | `#fff` |
| `--logo-filter` | `none` | `invert(1)` |
| `--sidebar-width` | `248px` | |
| `--header-height` | `60px` | |

- `:root` sets `color-scheme: dark`, `font-synthesis: none`, `font-family: DM Sans, sans-serif`, `color: var(--fg)` and `background: var(--bg)`.
- `:root[data-theme=light]` sets `color-scheme: light`, flips the toggle and sets `--logo-filter: invert(1)`.
- `.monochrome-logo { filter: var(--logo-filter) }` applies to the openai, anthropic, xai, kimi and zai logos, whose SVGs are white. See the sibling report `/tmp/claude-1002/slopalytics-facts/logos.md`.
- Per-family colours are inline strings such as `light-dark(#ae5235, #df9477)`, used as CSS `color` or SVG `fill`/`stroke`. The first value is light, the second dark.

**Font.** The first line of the stylesheet is `@import "https://fonts.googleapis.com/css2?family=DM+Sans:wght@400;450;500;550;600;650;700&display=swap"`. That loads one variable woff2 from fonts.gstatic.com (`dmsans/v17/...woff2`, latin subset). Weights in use:

| weight | used for |
|---|---|
| 400 | body |
| 450 | wordmark |
| 500 | h2, values, tooltip numbers |
| 550 | h3 section heads, on-frontier rows, legend, tooltip names, "Done" |
| 600 | lab monogram |

Fallback is `sans-serif`.

**Global resets.**

- `* { box-sizing: border-box }`. `body { margin: 0; user-select: none }`, with `input` text-selectable.
- `button, input { font: inherit }`. `button` has no background, border or padding, uses `color: inherit` and `cursor: pointer`. `button:disabled` has `opacity: .4` and `cursor: default`.
- `a` inherits colour with no underline.
- `button:hover, a:hover { color: var(--fg) }`. Specificity matters here; see the hover notes in section 6.
- `:focus-visible` on button, a and input: `outline: 2px solid var(--accent); outline-offset: 3px`. The `.chart-settings summary` uses offset 2px.
- `::selection` uses the accent background with `--on-accent` text. `-webkit-tap-highlight-color: transparent`. h2 and h3 have `margin: 0`.

**Border radii:** model rows 5px, context-menu items 5px, popover, tooltip and context menu 8px, checkbox `.selection` 3px, lab monogram 3px, active-tab underline 2px, dots 50%.

**z-index:** settings popover 20, context menu 100, tooltip 3 (7 on mobile), mobile sticky header 8, mobile sheet 10, sheet heading 1.

## 3. Desktop layout (grid)

- `.app` is a grid with rows `var(--header-height) minmax(0,1fr)` (60px plus the rest) and `height: 100dvh`. The document never scrolls on desktop.
- `.app-header` is a flex row with `align-items: center`, `padding: 0 28px` and `border-bottom: 1px solid var(--line)`.
  - Effective gap is 24px because `.app>.app-header { gap: 24px }` beats `.app-header { gap: 36px }` and the ≥1600px rule `.app-header { gap: 44px }`. The screenshot confirms 24px. At ≤1150px the gap is 16px; at ≤900px it is 0.
- `.body-layout` is a grid with columns `minmax(0,1fr) var(--sidebar-width)` (248px, border-box, including the 1px left border) and `min-height: 0`.
- `main` is a grid with rows `minmax(0,1fr) auto`: the chart feed, then the footer. The footer therefore sits under the charts only, not under the sidebar.
- `.chart-feed`: `overflow-y: auto`, `scroll-snap-type: y proximity`, `scrollbar-width: thin`, `scrollbar-color: var(--line-2) var(--bg)`, `position: relative`.
- `.chart-section`: `scroll-snap-align: start`, `height: 100%` (each chart fills the feed viewport exactly), `display: flex; flex-direction: column`, `padding: 18px 28px 10px`. `.chart-section + .chart-section` gets `border-top: 1px solid var(--line)`. The section id is the chart id and `aria-label` is the chart label.
  - `.chart-heading`: flex, space-between, centre, gap 16, margin-bottom 6. The h2 is 16px/500.
  - Chart controls on scatter charts only: the "Pareto line" check toggle, then a "Linear | Log" pair. These belong to the chart spec.
- `footer`: `border-top: 1px solid var(--line)`, `color: var(--fg-3)`, 11px, `padding: 9px 28px`, flex, space-between, centre, wrap, gap 12.
  - Left: "Data from " followed by a link "Artificial Analysis" (fg-2, `target=_blank rel=noreferrer`).
  - Right: `nav.footer-links` (gap 20, nowrap) whose last link uses the accent colour ("Try T3 Code"). Replace it with our own link.

## 4. Header

**Wordmark** `a.brand[href=location.pathname][aria-label="Slopalytics home"]`

- Contents: `<strong><span>slop</span>alytics</strong>`, nowrap, flex-shrink 0.
- `strong` is 24px, weight 450, `letter-spacing: -1.2px`. The `span` uses `color: var(--accent)`; the rest uses fg.
- The href is the bare path, so clicking it reloads with no query string and resets all state.
- Size by breakpoint: 21px at ≤1150px; 21px in a 52px-high flex cell with padding-left 16 at ≤900px; 19px at ≤420px.

**Section tabs** `nav.section-tabs` ("Benchmarks", "Usage")

- Flex, gap 14, `padding-right: 22px`, `border-right: 1px solid var(--line-2)`.
- Buttons: fg-3, 12px, min-height 36. Active: fg, with `aria-current="page"`.
- Switching section uses `history.pushState` and remembers each path's query string.
- Our rebuild has no Usage page, so this can be omitted.

**View tabs** `nav.view-tabs[aria-label="Chart views"]`

- `align-self: stretch` (full 60px), flex, gap 22, `overflow-x: auto`, `scrollbar-width: none`, `min-width: 0`.
- Buttons: fg-2, 12.5px, nowrap, flex centre, `position: relative`.
- Active button: fg, `aria-current="true"`, and a `::after` underline: 2px high, `background: var(--accent)`, `border-radius: 2px`, absolute `bottom: 0; left: 0; right: 0`.
- A `span.tab-divider` (1px × 14px, `var(--line-2)`, centred) sits before the third tab. It separates the two scatter charts from the four bar charts.
- Benchmark chart ids and labels:

| id | label | metric | scatter |
|---|---|---|---|
| `cost-intelligence` | Cost vs intelligence | cost | yes |
| `speed-intelligence` | Time per task vs intelligence | time | yes |
| `tokens-task` | Tokens per task | tokens | no |
| `tokens-total` | Total tokens | tokensTotal | no |
| `cost-task` | Cost per task | cost | no |
| `cost-total` | Total cost | costTotal | no |

- **Tab click:**
  1. Lock the scroll-spy with `{id, until: now + 1500ms}`.
  2. Set the `chart` URL param, removing it for the first chart.
  3. Call `document.getElementById(id).scrollIntoView({block: 'start', behavior})`, where `behavior` is `'auto'` under `prefers-reduced-motion: reduce` and `'smooth'` otherwise.
- **Tab bar auto-scroll:** when the active tab changes and the nav overflows (`scrollWidth > clientWidth`), set `nav.scrollLeft = activeButton.offsetLeft - 16`.
- **Scroll-spy.** Runs on the feed's `scroll` event and on window `scroll` (passive; the window is what scrolls on mobile).
  1. Let `hb` be the header's bottom edge. Set `threshold = hb + (innerHeight - hb) / 3`.
  2. The active chart is the last `.chart-section` whose `getBoundingClientRect().top <= threshold`.
  3. If a lock is live and the candidate differs from the locked id, ignore the event. Otherwise clear the lock and, if the candidate differs from the current chart, set the `chart` param.
- **On load,** and on every mobile/desktop media switch, call `document.getElementById(activeChartId)?.scrollIntoView({block: 'start'})`.

**Header actions** `div.header-actions` (`margin-left: auto`, flex, centre, gap 2)

`.icon-button` and the settings `summary` are 32×32, flex-centred, fg-2 colour, turning fg on hover. lucide icons use stroke 2 and `currentColor`.

1. **Theme toggle** `button.icon-button`. In dark mode it shows the sun icon at 16px with aria-label and title "Switch to light mode". In light mode it shows the moon icon at 16px with "Switch to dark mode".
2. **PNG download** `button.icon-button.desktop-only` (download icon, 15px).
   - aria-label and title are "Download PNG". After a failure they become "PNG download failed. Try again".
   - The button is disabled while an export is running, or when the active chart has no plottable rows. For scatter charts, plottable means metric not null, intelligence not null, and metric > 0 unless that chart is linear.
   - Export steps:
     1. Clone `#chart-<id>` and copy these computed styles onto every node as attributes: fill, fill-opacity, stroke, stroke-width, stroke-opacity, stroke-dasharray, font-family, font-size, font-weight, text-anchor, dominant-baseline, opacity, filter.
     2. Wrap the clone in a new SVG 44px taller. Add a background rect using the computed `background-color` of `html`, and a title `<text x=24 y=30 font-size=18 fill=html color>` containing the chart label.
     3. Rasterise at 2× via `Image` and `canvas`. Download as `slopalytics-<id>.png`, then revoke the object URL after 30 s.
3. **Settings** `details.chart-settings.desktop-only` (`position: relative`). This is not rendered on Usage.
   - `summary`: ellipsis icon at 17px, aria-label and title "Chart settings", `list-style: none`, webkit marker hidden. Colour is fg while `[open]` or hovered.
   - `div.settings-popover`:
     - Position `absolute; top: calc(100% + 10px); right: 0`, z-index 20.
     - Size and spacing: width 220, `max-width: calc(100vw - 32px)`, padding 16.
     - Look: `background: var(--surface)`, `border: 1px solid var(--line-2)`, `border-radius: 8px`.
     - Layout: flex column, `align-items: flex-start`, gap 14.
   - Popover contents, in order:
     - `span.control-label` "2D charts" (fg-3, 11px, margin-bottom -8px).
     - `button.check-button[aria-pressed=labels]`: a checkbox plus "Labels". Toggles `labels`.
     - `span.control-label` "Bar charts".
     - `button.check-button[aria-pressed=grouped]`: a checkbox plus "Group by model". Toggles `grouped`.
     - `button.check-button` with the arrow-down icon at 13px. When `sort=desc` the icon is rotated 180° and the text is "Highest first"; when `asc` the text is "Highest last". Clicking flips asc and desc. This button has no aria-pressed.
     - `button.check-button` with the rotate-ccw icon at 13px and the text "Reset highlights". It is shown only when line highlights exist, and clears them.
   - `.check-button`: inline-flex, gap 8, 12px, fg-2 (fg on hover), nowrap.
   - Checkbox `span.selection`: 12×12, `border: 1px solid var(--line-2)`, radius 3, colour `var(--on-accent)`. When `.checked` it uses the accent background and border and contains the lucide `check` icon at 11px, stroke-width 3, rendered 10×10.
   - The popover closes on window `pointerdown` outside the details element. It also closes on Escape, either from the window handler or from the details' own keydown, which then focuses the summary.
4. **Mobile toggle** `button.mobile-only.mobile-filter-toggle`. It contains the sliders-horizontal icon at 14px, " ", `span.filter-label` "Models", " ", and `span` with the selected-family count. Clicking it opens the sheet. Styling is in section 12.

## 5. Sidebar container

`aside.sidebar`:

- Layout: flex column, gap 18, `height: 100%`, `min-height: 0`, `overflow: auto`.
- Padding `16px 18px`. Its content width at 248px is 211px.
- Look: `border-left: 1px solid var(--line)`, `scrollbar-width: thin`, `scrollbar-color: var(--line-2) var(--bg)`.
- `.sidebar > *` has `flex-shrink: 0`.
- For short desktop viewports (`width >= 761px and height <= 820px`) the gap is 14 and padding-top is 12.

Children, in order:

1. `div.side-heading`: "Models N", a reset button, and a mobile-only "Done".
2. `div.search`.
3. `div.effort-filter[role=group][aria-label=Reasoning]`.
4. One `section.model-section[aria-label=<label>]` per non-empty group: Frontier, Notable, Other. While searching, a single Results group replaces them.
5. `p.side-note` "No models match “q”." when every group is empty.
6. `div.browse-options`, hidden while a search query is active.
7. Mobile only: `section.sheet-options[aria-label="Chart settings"]` with h3 "Charts" and the same controls as the settings popover.

### 5.1 Heading

`.side-heading`: flex, centre, gap 8, margin-bottom -6px, so the visual gap to the search box is 12px.

- `h2`: `flex: 1`, 15px/500, text "Models ".
  - A `<span>` after it shows `selected.length`: fg-3, 11px/400, tabular-nums, margin-left 6.
  - The count is the length of the URL selection array. It counts families even when they have no visible rows.
- Reset button: 24×24, fg-3 (no hover colour change, see section 6), rotate-ccw icon at 14px, title and aria-label "Reset selection". Behaviour is in section 9.
- `button.mobile-only.sheet-done` "Done" closes the sheet.

### 5.2 Search

`.search`: height 32, flex, centre, gap 8, fg-3, `border-bottom: 1px solid var(--line-2)`. The border turns accent on `:focus-within`.

- Search icon at 14px.
- `input[aria-label="Find a model"][placeholder="Find models"]`: flex 1, `min-width: 0`, no border, background or outline, 12.5px, fg. The placeholder is fg-3.
- Trailing element:
  - While the raw value is empty: `<kbd>/</kbd>` (font inherit, 11px).
  - Otherwise: `button[aria-label=Clear search][title=Clear search]` with the x icon at 14px. Clicking it clears the query and refocuses the input.
- Semantics:
  - `q = value.trim().toLowerCase()`.
  - A family matches when `(name + " " + labName).toLowerCase().includes(q)`. This is a plain substring test with no fuzzy matching; "gmni" finds nothing.
  - The full name is used, so "claude" matches even though rows display it stripped.
  - Filtering runs on every keystroke with no debounce. The query is never written to the URL.
  - Enter does nothing.
- Escape inside the input:
  - If the raw value is non-empty: `preventDefault`, `stopPropagation`, clear the value. Focus stays in the input.
  - If empty: the event bubbles. The aside closes the mobile sheet; otherwise the window handler closes the sheet and the settings popover.
- `/` anywhere, unless the event target is an `<input>`: `preventDefault`, open the mobile sheet (state flag, harmless on desktop), then `setTimeout(0)` and focus the input. Modifier keys are not checked.
- While a query is active:
  - Groups are replaced by one group `{id: 'search', label: 'Results'}`. It contains every family in the dataset (`rr`) that matches, sorted with the standard comparator. The open-weights, older and Show-all toggles are ignored here.
  - The Frontier and Notable header toggles are hidden.
  - `browse-options` is hidden.
- When nothing matches, render `p.side-note` (fg-2, 12px) with the exact text `No models match “` + `value.trim()` (original case) + `”.`, using curly quotes.

### 5.3 Reasoning toggles

`.effort-filter`:

- `h3` "Reasoning" is 12px/550.
- The child `div` is a wrapping flex row with gap `4px 8px` and margin-top 8.

**Which levels are shown.**

1. Take every variant row whose family is in `selected`. Visibility on the chart does not matter.
2. Sort by `effortOrder` ascending and keep the first occurrence of each `effort` value.

The list therefore changes with the selection. With nothing selected, the h3 renders with an empty row. Levels in the dataset:

| effort | label shown | effortOrder | rows |
|---|---|---|---|
| none | `none` (effortLabel is "Non-reasoning") | 0 | 294 |
| minimal | minimal | 10 | 4 |
| low | low | 20 | 31 |
| medium | medium | 30 | 30 |
| default | default (label "Default", lowercased) | 35 | 220 |
| high | high | 40 | 57 |
| xhigh | xhigh | 50 | 30 |
| max | max | 60 | 30 |

The label rule is `effort === 'none' ? 'none' : effortLabel.toLowerCase()`. With the default selection the row is `none low medium high xhigh max`, with `none` struck through.

**Button.** `button[aria-pressed = !excluded.includes(effort)]`: fg, 11.5px. When `aria-pressed=false` it is fg-3 with `text-decoration: line-through`, and this rule outranks the global hover colour. Clicking toggles membership of `effort` in `excluded`: remove it if present, otherwise append it.

**Effect on the chart.** Visible rows are `models.filter(m => selected.includes(m.family) && !excluded.includes(m.effort))`. An excluded level that no selected family has stays in `excluded` but is not shown as a button.

**Default.** `excluded = ['none']`, so non-reasoning variants are hidden by default. In their data, gpt-6-luna-non-reasoning is hidden and 34 variants are visible.

### 5.4 Model groups

Each group is a `section.model-section`.

- `.section-head`: flex, `align-items: baseline`, gap 10, margin-bottom 4.
- `h3`: `flex: 1`, 12px/550.
- Header toggle buttons: fg-3, 11.5px. `aria-pressed=true` shows the accent colour. Hover colour does not change.

**Frontier**: the hard-coded families map `L`, with tier and colour. Colours are `light-dark(light, dark)`.

| family | tier | light | dark |
|---|---|---|---|
| gpt-6-astra | Large | #303840 | #f1f3f5 |
| gpt-6-1-sol | Medium | #586878 | #c5cbd3 |
| gpt-6-luna | Small | #748292 | #939daa |
| claude-opus-5-5 | Large | #ae5235 | #df9477 |
| claude-fable-5-1 | Large | #903e2b | #cc785c |
| claude-sonnet-5-5 | Medium | #bd6948 | #f0b99f |
| claude-haiku-5-5 | Small | #c4805f | #b98a74 |
| gemini-4-argon | Large | #218347 | #56ca80 |
| gemini-3-8-flash | Medium | #247a3c | #34a853 |
| grok-4-7 | Large | #6d55bd | #9b94ee |

- Display order (sorted with the comparator in section 7): GPT-6.1 Sol, GPT-6 Luna, GPT-6 Astra, Haiku 5.5, Sonnet 5.5, Opus 5.5, Fable 5.1, Gemini 4 Argon, Gemini 3.8 Flash, Grok 4.7.
- Families missing from the dataset are skipped.
- **Tier toggles.** Shown only when not searching. Three buttons, in the order `Small`, `Medium`, `Large`, sit after the h3.
  - The tier set is every key of `L` with that tier. Small is {gpt-6-luna, claude-haiku-5-5}. Medium is {gpt-6-1-sol, claude-sonnet-5-5, gemini-3-8-flash}. Large is {gpt-6-astra, claude-opus-5-5, claude-fable-5-1, gemini-4-argon, grok-4-7}.
  - `aria-pressed` is true when every family in the set is selected.
  - Click: if all are selected, remove them all; otherwise append the missing ones to the end of the selection in tier-list order, de-duplicated.
  - Default state: Small and Large are pressed; Medium is not.
  - Observed URL after clicking Medium: `?models=gpt-6-astra,gpt-6-1-sol,gpt-6-luna,claude-opus-5-5,claude-fable-5-1,claude-haiku-5-5,gemini-4-argon,grok-4-7,claude-sonnet-5-5,gemini-3-8-flash`, with the count at 10.

**Notable**: the hard-coded families map `Rt`, colours only.

| family | light | dark |
|---|---|---|
| mimo-v2-6-pro | #b85212 | #ff8b45 |
| muse-spark-1-3 | #236bbd | #5ea4ff |
| kimi-k3 | #ab3f83 | #ee86c4 |
| glm-5-3 | #8e7318 | #ecd36e |
| glm-5-3-flash | #7c6b2e | #b9a453 |
| deepseek-v4-pro | #157d83 | #52cdd2 |
| deepseek-v4-1-flash | #216b70 | #33979c |

- Display order: Muse Spark 1.3, Kimi K3, GLM 5.3 Flash, GLM-5.3, DeepSeek V4.1 Flash, DeepSeek V4 Pro 0813, MiMo-V2.6-Pro.
- **"All" toggle.** Shown only when not searching. It works like the tier toggles, over all seven Notable families. It is not pressed by default because no Notable family is selected by default.

**Other**: every remaining family, sorted. It contains the families that pass this filter:

```
selected.includes(f)  ||  (showAll && (openWeights || !f.open) && (older || !f.deprecated))
```

- Selected Other families therefore always appear, and with them the "Other" header, even while "Show all models" is collapsed. This happens, for example, after a URL or context-menu selection.
- `deprecated` is the dataset flag OR membership in the hard-coded set `zt = {'gemini-3-5-flash-lite'}`.
- Counts in their data (502 families: 10 Frontier, 7 Notable, 485 Other):
  - Show all alone adds 36 closed, current families.
  - Open weights adds 133 open, current families.
  - Older adds 316 deprecated families. Open deprecated families need both toggles.
  - With both toggles on, all 502 families are listed.

**Browse options** `div.browse-options` (hidden while searching)

- `border-top: 1px solid var(--line)`, padding-top 14, flex column, gap 10.
- `button[aria-expanded]`: fg-2, 12px, left-aligned. Text is "Show all models", or "Hide other models" while expanded.
- While expanded, a `div` (flex, gap 14) holds two toggles, both `aria-pressed`, both off by default, fg-3 at 11.5px and accent when pressed:
  - "Open weights" includes open families.
  - "Older" includes deprecated families.
- None of these three states is stored in the URL. Reset sets all three to false.

### 5.5 Model row anatomy

`button.model-row[aria-pressed=selected][title="<name> · <labName>"]`. Class `on-frontier` or `off-frontier` is added only when Pareto mode applies (section 8).

- **Box.**
  - Size and alignment: `width: calc(100% + 12px)`, `margin: 0 -6px`, `padding: 0 6px`. The hover background therefore bleeds 6px past the column.
  - `min-height: 26px`: 29px at ≥1600px, 24px on short desktops, 44px on mobile.
  - Layout: flex, centre, gap 9, left-aligned.
  - Type and shape: 12.5px (13px at ≥1600px, 15px on mobile), `border-radius: 5px`.
- **Colours.**
  - Unselected text is fg-3; selected (`aria-pressed=true`) is fg.
  - Hover, only under `@media (hover:hover)`: `background: var(--hover)`. Text also turns fg, because the global `button:hover` outranks `.model-row`.
- **Children, in order:**
  1. Lab logo, 14×14. With a known logo it is `img.lab-logo` (plus `.monochrome-logo` for openai, anthropic, xai, kimi and zai) using a data-URI SVG and `object-fit: contain`. Otherwise it is `span.lab-logo.lab-monogram`: the first character of `labName`, 14×14, font-size `14*0.55` = 7.7px, weight 600, line-height 1, background `--hover`, colour fg-2, radius 3, inline-flex centred. Logo opacity is .4, rising to 1 when the row is selected or hovered.
  2. `span.model-name`: `name.replace('Claude ', '')`, which removes only the first occurrence. It is `flex: 1`, nowrap, with ellipsis.
  3. `i.model-dot`, styled `style="color: <family colour>"`: 7×7, round, flex-shrink 0, `box-shadow: inset 0 0 0 1px` (a currentColor ring), opacity .5. When selected it has opacity 1 and is filled with `currentColor`.
- **Family colour** (`Ut`): `L[family].color`, else `Rt[family].color`, else the lab colour, else the fallback `light-dark(#637082, #a4adb9)`.

  | lab id | name | light | dark |
  |---|---|---|---|
  | openai | OpenAI | #303840 | #f1f3f5 |
  | anthropic | Anthropic | #ae5235 | #df9477 |
  | google | Google | #218347 | #56ca80 |
  | xai | xAI | #6d55bd | #9b94ee |
  | meta | Meta | #236bbd | #5ea4ff |
  | kimi | Kimi | #ab3f83 | #ee86c4 |
  | zai | Z AI | #8e7318 | #ecd36e |
  | deepseek | DeepSeek | #157d83 | #52cdd2 |
  | xiaomi | Xiaomi | #b85212 | #ff8b45 |

- **Interactions.**
  - Click toggles the family in `selected`. Removal deletes it in place; addition appends it to the end.
  - `contextmenu` opens the context menu for this model (section 10).
  - `pointerenter` with `pointerType === 'mouse'` sets `focusFamily`. Keyboard `focus` does the same, but only when `:focus-visible`. `pointerleave` and `blur` clear it.
  - `focusFamily` makes the chart emphasise that family, the same way as hovering a chart label. On scatter charts, other families' lines drop to .15 opacity and the focused line widens from 2.25 to 3.5. It applies only when the family has visible rows.
- **Representative row per family:** the dataset is de-duplicated by `family`. The map keeps the first position and the last row's values. Name, lab, open and deprecated are identical within a family in their data.

## 6. Effective hover colours (specificity quirks)

`button:hover` has specificity (0,1,1). Rules with the same specificity that appear later in the file win, so these elements do not change colour on hover:

- `.view-tabs button` (stays fg-2)
- `.side-heading button` (reset, stays fg-3)
- `.section-head button` (tier, All)
- `.browse-options>button` and `.browse-options div button`
- struck reasoning buttons

These do turn fg on hover: `.section-tabs` buttons, `.icon-button`, `.check-button`, `.model-row`, and footer links.

Explicit hovers:

| element | hover result |
|---|---|
| `.pareto-toggle` | accent |
| `.chart-scale button` | fg |
| `.context-menu button:hover/:focus` | `--hover` background, fg text |
| `.chart-settings summary` | fg |

## 7. Sorting comparator (Frontier, Notable, Other, Results)

1. Lab rank: the index in the lab order `openai, anthropic, google, xai, meta, kimi, zai, deepseek, xiaomi`. Unknown labs share rank 9.
2. `labName.localeCompare` ascending. This orders unknown labs alphabetically, e.g. AI21 Labs, AI9Stars, Alibaba, Allen Institute for AI, Amazon.
3. `released` descending (string compare, null treated as "").
4. `name` descending, using `localeCompare(other, 'en', {numeric: true})`.

Within one lab the newest model comes first; the observed "opus" search returns Opus 5.5, Opus 5, 4.8, ..., "3 Opus". The xai `labName` in the data is "SpaceXAI", but the context menu uses the lab-table name "xAI".

## 8. Pareto interaction with rows

When the active chart is a scatter chart and `frontier=true`:

- Compute the Pareto set over the visible rows of that chart's metric. Plottable rows are sorted by metric (lower first for cost and time), with ties broken by higher intelligence. A row is kept when its intelligence exceeds the running maximum.
- Each selected row gets `.on-frontier` (font-weight 550) if its family has at least one Pareto variant, otherwise `.off-frontier` (opacity .35, back to 1 on hover or focus-visible).
- Unselected rows get neither class.

## 9. Reset semantics

**Sidebar reset button** (rotate-ccw):

1. Set `selected` and `excluded` to their defaults.
2. Clear the search text.
3. Turn off Show all models, Open weights and Older.
4. Clear the line highlights (family highlights from legend or label clicks).
5. Bump a key so every chart remounts, which drops the chart's internal hover, pin and label-hover state.
6. Close the context menu.
7. Clear the whole benchmark nuqs group (`setState(null)`), so `models`, `hide-reasoning`, `linear`, `frontier`, `labels`, `grouped` and `sort` all return to their defaults. The `chart` param (the current tab) is kept.

**Chart empty-state "Reset filters"** (`button.text-button`, accent, 12px) does steps 1-6 only. `linear`, `frontier`, `labels` and the other display params are untouched.

The empty-state title is chosen as follows:

- `No models selected` when `selected` is empty.
- `No reasoning levels enabled` when the selection is non-empty but no rows survive the reasoning filter.
- `No data for this view` otherwise, meaning rows exist but none have this metric.

`.empty` is a centred flex column with gap 10; its `strong` is 17px/500.

**Context-menu selection actions:**

- "Reset model selection" sets `selected` to its default.
- "Clear model selection" sets `selected = []`, which writes `?models=`.

## 10. Context menu (right-click on a sidebar row, chart point, label or empty chart)

`div.context-menu[role=menu][aria-label=title]`:

- Position `fixed`, z-index 100. It opens at the click point, falling back to the element's left and bottom edges for keyboard-triggered events, and is clamped 8px inside the viewport.
- Size: width 250, `max-width: calc(100vw - 16px)`, `max-height: calc(100dvh - 16px)`, `overflow-y: auto`.
- Look: padding 6, 12px text, surface background, 1px line-2 border, radius 8.
- Title `.context-menu-title`: accent, padding 8, `overflow-wrap: anywhere`. It shows the model's full name, or the lab name, or "Chart".
- Items are `button[role=menuitem]`: block, full width, fg-2, padding 8, radius 5. Hover or focus gives the `--hover` background and fg text.
- `.menu-divider` items get `border-top: 1px solid var(--line-2)`, radius 0, margin-top 5.

Items for a model, in order:

1. "Hide this family" or "Show this family".
2. "Show only this family".
3. "Show all except this family", over the listed families.
4. "Highlight this family" or "Unhighlight this family".
5. Divider, then "Show all {Lab}". This adds the lab's listed families.
6. "Hide {Lab}". This removes every family of the lab, listed or not.
7. "Show only {Lab}", listed families only.
8. "Show all except {Lab}", listed families only.
9. Divider, then "Show all listed models".
10. "Reset model selection".
11. "Clear model selection".
12. "Clear highlights", only when highlights exist.

"Listed" means Frontier + Notable + Other, with Other filtered by the same rule as the sidebar. During a search, all Other families count as listed.

Behaviour:

- Keyboard: ArrowDown and ArrowUp wrap, Home and End jump to the ends, Escape and Tab close.
- The first item is focused on open.
- The menu closes on outside `pointerdown`, on `resize`, and on capture-phase `scroll` outside the menu.
- Focus returns to the origin element when the menu closes.

## 11. Theme

- React state `dark = true` on every load. The theme is not persisted (no localStorage), does not appear in the URL (the observed `url_light` was `/`), and ignores `prefers-color-scheme`.
- A layout effect sets `document.documentElement.dataset.theme` to `'dark'` or `'light'` and sets `meta[name=theme-color]` to `#000000` or `#ffffff`.
- The toggle simply flips the state.
- In our rebuild we could keep "dark by default, not persisted" for fidelity. Persisting would be a deliberate deviation.

## 12. Mobile (`max-width: 900px`), plus other breakpoints

JS reads `matchMedia('(max-width: 900px)')` through `useSyncExternalStore`, giving the boolean `compact`. The CSS uses `@media (width<=900px)`.

**Page flow**

- `.app { display: block; height: auto }`. `.body-layout` and `main` are `display: block`. The window scrolls.
- `.chart-feed` has no scroll-snap and `overflow: visible`.
- `.chart-section` has `height: auto`, `padding: 20px 16px 24px` and `scroll-margin-top: 95px`. 95px is the 52px header row + the 42px tab row + 1px.
- Footer padding: `18px 16px calc(28px + env(safe-area-inset-bottom))`.
- `.desktop-only` is `display: none !important`, which hides PNG and settings. `.mobile-only` becomes `display: inline-flex !important` with `align-items: center` and gap 6. It is `display: none !important` on desktop.

**Sticky header**

- `.app-header`: `position: sticky; top: 0; z-index: 8; background: var(--bg)`, `flex-wrap: wrap`, `gap: 0`, `padding: 0`, `height: auto`.
- First row:
  - `.brand`: 52px high, padding-left 16, 21px type.
  - `.section-tabs`: margin-left 22, gap 14, no border, buttons min-height 44 at 12px.
  - `.header-actions`: 52px high, padding-right 10.
- Second row, `.view-tabs`: `order: 3`, `width: 100%`, height 42, `padding: 0 16px`, gap 20, buttons 13.5px, `border-top: 1px solid var(--line)`, scrolling horizontally.

**"Models N" button** `.mobile-filter-toggle`

- Height 40, `padding: 0 6px`, 14px, fg colour.
- Contents: sliders icon, then "Models" (`.filter-label`, fg, 13px), then the count (span, fg-3, 12px).
- At ≤420px the gap is 5. At ≤370px the "Models" label is hidden and only the icon and count remain.
- Clicking opens the sheet. While the sheet is open, `document.body.style.overflow = 'hidden'`.

**Full-screen sheet** (`aside.sidebar.open`)

- `.sidebar` is `display: none` unless `.open`, which makes it `display: flex`.
- Placement: `position: fixed; inset: 0; z-index: 10; height: 100dvh`.
- Look: `background: var(--bg)`, no left border.
- Padding: `0 16px calc(24px + env(safe-area-inset-bottom))`.
- `.side-heading`:
  - Position: `position: sticky; top: 0; z-index: 1`, height 56.
  - Look: `background: var(--bg)`, `border-bottom: 1px solid var(--line)`.
  - Spacing: `margin: 0 -16px -6px; padding: 0 16px`.
  - The h2 is 17px.
  - `.sheet-done` "Done": accent, 15px/550, height 40, `padding: 0 4px 0 12px`. It closes the sheet.
- Escape inside the sheet closes it and focuses `.mobile-filter-toggle`. The window Escape handler also closes it.
- Touch sizing:
  - Search: height 42, input font 16px (avoids iOS zoom), kbd hidden.
  - Reasoning, tier and All buttons and browse sub-toggles: min-height 32, 14px. The reasoning row gap is `0 16px`.
  - h3: 14px.
  - Model rows: min-height 44, 15px.
  - `.browse-options>button`: min-height 32, 14px.
- An extra final block, `section.sheet-options`:
  - Layout: `border-top: 1px solid var(--line)`, padding-top 16, flex column, `align-items: flex-start`, gap 14.
  - Content: h3 "Charts" followed by the same controls as the desktop popover (2D charts/Labels, Bar charts/Group by model/sort, Reset highlights).
  - Sizing: `.control-label` is 12px with margin-bottom -6px. `.check-button` has min-height 32 at 14px.

**Charts in compact mode** (details belong to the chart spec)

- `.chart-canvas` gets `aspect-ratio: 1/1.2; flex: none`.
- The chart h2 is 18px, flex, with a baseline `span` unit (fg-3, 12px/400) for bar charts.
- `.chart-heading` wraps with gap `4px 16px`. `.chart-controls` takes `flex: 1 0 100%` with space-between. The Pareto toggle and scale buttons have min-height 44, and the scale gap is 10.
- The SVG uses compact margins. In-plot labels are replaced by a legend below the chart.
- Bar charts render as a "dot plot" list instead of SVG bars.

**Two-column legend** `.chart-legend`

- Shown only when compact, the chart is a scatter chart, `labels=true`, and rows exist.
- Layout: grid `repeat(2, minmax(0,1fr))`, gap `2px 12px`, padding-top 10.
- One `button[aria-pressed=highlighted]` per family. Its content is the family's highest-intelligence variant: logo at 13px plus the name with "Claude " stripped.
  - Text: 13px/550, nowrap, `overflow: hidden`, colour = family colour.
  - Layout: flex, gap 7, min-height 32.
  - Order is by that variant's intelligence, descending, filled row-major: Opus 5.5 | Fable 5.1, GPT-6 Astra | Gemini 4 Argon, and so on.
- Clicking toggles a line highlight for the family.
- `.dim` (opacity .35) applies to families that are not emphasised whenever some family is highlighted, pinned or focused.

**Tap and sticky tooltip card**

- On compact scatter charts, points have `pointer-events: none`. A tap on the SVG finds the nearest point in SVG units and pins it if it is within 40 units; otherwise the pin clears.
- The tooltip becomes a card in the flow below the legend:
  - Position: `position: sticky; bottom: calc(10px + env(safe-area-inset-bottom)); z-index: 7`, margin-top 14.
  - Size: `width: auto; max-width: none`, with top, left and right auto.
  - Look: surface background, line-2 border, radius 8.
- When not comparing, the card is a 2-column grid with column-gap 20 and padding `12px 14px`. Non-value children span both columns.
- Contents:
  - The head: logo at 18px, the coloured full name, and a close button (x, 20×20).
  - `p` "<effortLabel> · Pinned".
  - Value pairs, shown as label then value: Intelligence index 57.6, Cost per task $5.98, Tokens per task 119.2k, Time per task 13m 4s.
  - The "Artificial Analysis" link (accent, underline).
- A pinned point also dims the other legend entries.

**Other breakpoints (desktop)**

| query | changes |
|---|---|
| `width >= 1600px` | view-tabs gap 26, tab font 13px; model rows 29px/13px. The `.app-header` gap of 44 is overridden to 24. |
| `width >= 761px and height <= 820px` | sidebar gap 14, padding-top 12; model rows min-height 24 |
| `width <= 1150px` | header padding `0 18px`, gap 16; brand 21px; view-tabs gap 16 at 12px; section-tabs gap 10, padding-right 16; chart-section side padding 18; footer padding `9px 18px` |
| `width <= 420px` | section-tabs gap 11, margin-left 15, font 11px; brand 19px; header-actions padding-right 8; mobile toggle gap 5 |
| `width <= 370px` | `.filter-label` hidden |

## 13. URL state (nuqs 2.10.1)

General rules:

- Writes use `history.replaceState`, so no history entries are added. They are throttled to 50ms (120 or 320ms on Safari).
- `scroll: false`, shallow updates.
- Params not managed by nuqs are preserved. Existing keys keep their position; new keys are appended.
- **Default omission (`clearOnDefault`):** a value equal to its default is deleted from the URL. List equality is "same length and every item included", so any order of the default list counts as the default and is omitted.
- **Encoding:** values are written raw except for these escapes: `%`→`%25`, `+`→`%2B`, space→`+`, `#`→`%23`, `&`→`%26`, `"`→`%22`, `'`→`%27`, `` ` ``→`%60`, `<`→`%3C`, `>`→`%3E`, and control characters. Commas stay literal. Keys escape `# & + = ?`.
- **Parsing:**
  - Missing key: the default.
  - Literal or boolean parse failure: the default. A boolean is `value.toLowerCase() === 'true'`, so any other string, including `1` or `0`, means false.
  - Lists: `value.split(',')` filtered to known values. Unknown ids are silently dropped, and an empty value parses as `[]`, which is not the default.

| state | URL key | parser | default | non-default examples |
|---|---|---|---|---|
| chart | `chart` | literal of the 6 benchmark ids + `balance`, `models`, `harnesses` | none, but the app writes `null` for the first chart id | `?chart=tokens-task` |
| selected | `models` | comma list ⊂ all dataset families | `gpt-6-astra, gpt-6-1-sol, gpt-6-luna, claude-opus-5-5, claude-fable-5-1, claude-haiku-5-5, gemini-4-argon, grok-4-7`: all Frontier keys except `claude-sonnet-5-5` and `gemini-3-8-flash`, 8 families | `?models=...,muse-spark-1-3`; empty selection is `?models=` |
| excluded | `hide-reasoning` | comma list ⊂ all dataset effort values | `['none']` | `?hide-reasoning=low`; showing every level is `?hide-reasoning=` |
| linear | `linear` | comma list ⊂ scatter chart ids | `[]` (both scatter charts on log) | `?linear=cost-intelligence` |
| frontier (Pareto line) | `frontier` | boolean | false | `?frontier=true` |
| labels | `labels` | boolean | true | `?labels=false` |
| grouped | `grouped` | boolean | true | `?grouped=false` |
| sort | `sort` | literal asc/desc | asc | `?sort=desc` |

The `frontier` URL param is the Pareto line toggle. It has nothing to do with the sidebar's "Frontier" group.

**Legacy `#view` migration.** This runs once before render (`kn()`).

1. Read `new URLSearchParams(location.hash.slice(1)).get('view')`. If it is absent, stop.
2. `JSON.parse` the value, catching errors. Only a non-null object is used; anything else becomes `{}`.
3. Map the old view names `usage-balance`→`balance`, `model-usage`→`models`, `harness-usage`→`harnesses`. Then parse with the chart literal parser, where unknown means null. If the result is the first chart of either list, use null.
4. On `/usage`, only `chart` is migrated. Otherwise, call the serializer with the current `location.search` and:
   - `chart`
   - `selected`: `view.selected` if it is a string array, else null
   - `excluded`: `view.excluded` if it is a string array, else null
   - `linear`: the scatter ids where `(view.logByView?.[id] ?? view.log) === false`
   - `frontier`: `view.frontier === true || null`
   - `labels`: false if `view.labels === false`, else null
   - `grouped`: same rule as labels
   - `sort`: `'desc'` if `view.descending === true`, else null
5. Defaults are omitted, as usual. Finally `history.replaceState(null, '', pathname + newSearch)`, which drops the hash.

Separately, the paths `/t3-code` and `/popularity` are rewritten to `/usage` with the query string kept.

## 14. Keyboard summary

- `/`: focus search (opens the sheet on mobile). Ignored when the target is an input.
- Escape, in priority order:
  1. In a non-empty search: clear it.
  2. In the open mobile sheet: close it and refocus the toggle.
  3. In the settings popover: close it and refocus the summary.
  4. Globally: close the sheet and settings. The chart's own window listener also clears the pin, hover, label hover and all line highlights.
- Context menu: arrows, Home, End, Escape and Tab (section 10).

## 15. Notes for a vanilla reimplementation in our repo

- **State.** Keep one `state` object: `{chart, selected[], excluded[], linear[], frontier, labels, grouped, sort}` plus ephemeral `{query, showAll, openWeights, older, highlights[], focusFamily, sheetOpen, dark}`.
  - Write the URL with `history.replaceState`, using the encoding and default-omission rules above. A 50ms throttle is optional.
  - Parse on load and on `popstate`.
- **List derivation per render:**
  1. Build `families`: one representative per family, then `frontier = Object.keys(L) ∩ families`, `notable = Object.keys(Rt) ∩ families`, and `other` = the rest. Sort each list with the section 7 comparator.
  2. Apply search, or the Other visibility rule.
  3. Build the reasoning list from all variants of the selected families.
- **Data.** Our scraper's `models.json` must supply `family`, `lab`, `labName`, `released`, `open`, `deprecated`, `effort`, `effortLabel`, `effortOrder`, `name`, `intelligence` and `cost`. See `/tmp/claude-1002/slopalytics-facts/mapping.md` for how to derive effort, and `/tmp/claude-1002/slopalytics-facts/logos.md` for lab logos.
  - Unknown labs fall back to a monogram (first letter of labName) and the grey fallback colour.
  - The `L` and `Rt` lists are hand-curated and specific to the model generation. Treat them as config.
- **Single-chart page.** For a single "Cost vs intelligence" page:
  - The view tabs, scroll-snap feed and scroll-spy reduce to one section.
  - Keep the 60px header, the 248px sidebar grid, the footer under the chart, and the ≤900px sheet behaviour.
