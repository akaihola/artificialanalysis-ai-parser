# Slopalytics "Cost vs intelligence" chart: implementation spec

Sources (untrusted, read only, nothing executed):

- `/tmp/claude-1002/slopalytics-research/bundle.pretty.js`
  - chart component `Qn`: lines 30078-30755
  - helpers: lines 28600-28800 (colors `L`/`Rt`/`Bt`/`Ut`, metric table `Wt`, formatter `Kt`, multiplier `R`, Pareto `Yt`, bar grouping `Jt`, sidebar order `Xt`)
  - logos: lines 29201-29275 (`Hn`/`Un`/`Bn`)
  - views and state: lines 29077-29200 (`gn`, `bn`)
  - PNG export `er` and context menu `tr`: lines 30842-30960
  - app shell `mr`: lines 31031-31619
- `/tmp/claude-1002/slopalytics-research/style.pretty.css`
- Screenshots `02`–`22`, `interact_log.json` and `mobile_log.json`. These confirm the geometry: the desktop viewBox is 1136×741, the mobile one 358×429.

Cross-checks with screenshots are marked (verified). My own reimplementation of the formatter and tick rules is in `/tmp/claude-1002/slopalytics-facts/scripts-chartspec/fmt.mjs`, and its outputs are quoted in §9.

One component (`Qn`) draws every chart: the scatter charts ("Cost vs intelligence" with metric `cost` and "Time per task vs intelligence" with metric `time`) and the bar charts. This spec covers scatter mode. Bar mode is summarised in Appendix B.

---

## 1. Data the chart consumes

Each row is one model variant with these fields: `id, family, name, lab, labName, effort, effortLabel, effortOrder, deprecated, intelligence, cost, tokens, time` (plus `speed, tokensTotal, costTotal` for other views).

Effort values in their dataset (`effort`, `effortLabel`, `effortOrder`):

- `none`, "Non-reasoning", 0
- `minimal`, "minimal", 10
- `low`, "low", 20
- `medium`, "medium", 30
- `default`, "Default", 35
- `high`, "high", 40
- `xhigh`, "xhigh", 50
- `max`, "max", 60

The tooltip shows `effortLabel` verbatim, for example "max". The sidebar uses `effort === 'none' ? 'none' : effortLabel.toLowerCase()`.

`deprecated` is overridden to true for the family `gemini-3-5-flash-lite` (set `zt`).

Rows passed to the chart (`rows`) are the dataset rows whose `family` is in `selected` and whose `effort` is not in `excluded`, in dataset order. Dataset order is roughly alphabetical by `id`, case-insensitive. This order matters because it sets the SVG paint order of families.

The chart's visible set `O` keeps rows with `row[metric] !== null`, `intelligence !== null` and, in log mode, `row[metric] > 0`.

Default app state:

- `selected` = all frontier families except `claude-sonnet-5-5` and `gemini-3-8-flash`
- `excluded` = `['none']`
- `linear` = `[]` (both scatter charts start on log)
- `frontier` = false
- `labels` = true
- `grouped` = true
- `sort` = `asc`

URL keys: `chart`, `models` (= selected), `hide-reasoning` (= excluded), `linear` (comma list of scatter view ids that are linear, e.g. `?linear=cost-intelligence`), `frontier=true`, `labels`, `grouped`, `sort`. Highlights, pin, hover and theme are not stored in the URL. The theme always starts dark.

## 2. Layout and sizing

The SVG fills `.chart-canvas` (flex:1). A ResizeObserver reports `Math.floor(contentRect.width/height)`. Before the first measurement the size is 1120×430. The viewBox is `0 0 W H`, so 1 SVG unit = 1 CSS px.

`compact` = `matchMedia('(max-width: 900px)')`.

| symbol | desktop | compact |
|---|---|---|
| W (viewBox width) | `max(740, measuredW)` | `max(280, measuredW)` |
| H (viewBox height) | `max(240, measuredH)` | same |
| font scale `v` | `min(1.15, max(1, W/1200))` | `1` |
| plot left `X0` | 64 | 40 |
| plot right `X1` | `W - 235` (the 235 px gutter holds the labels) | `W - 14` |
| plot bottom / x-axis `Y0` | `H - 60` | `H - 46` |
| plot top `Ytop` | 30 | 30 |
| max right labels `S` | `min(16, floor((Y0-30)/24) + 1)` | unlimited (shown as an HTML legend) |
| x-axis title y | `Y0 + 57` | `Y0 + 40` |
| x-axis title size | `13*v` | `12*v` (= 12) |

The right gutter stays 235 px even when labels are turned off.

Mobile: `.chart-canvas { aspect-ratio: 1/1.2; flex: none }`, which gives a 358 px wide canvas a height of 429 (verified).

Font scaling: only text uses `v`. Tick labels are `12v`, the y-axis title `12v`, series labels `13v` and crosshair value labels `11v`. Logo sizes, the 24 px label spacing, radii and stroke widths are not scaled.

SVG root attributes:

- `font-family: var(--chart-font, 'DM Sans', sans-serif)`. `--chart-font` is never defined, so DM Sans is used. Google Fonts loads DM Sans weights 400, 450, 500, 550, 600, 650 and 700.
- `role="img"`
- `aria-label="Cost per task versus Intelligence Index"`
- `id="chart-cost-intelligence"`

The first child is a background `<rect width=W height=H fill="var(--bg)">`.

## 3. Scales and domains

Let `vals = O.map(r => r[metric])` and `iq = O.map(r => r.intelligence)`.

- **xMax** `= max(max(vals) or 1, 1e-6) * 1.08` (scatter; bar charts use 1.15).
- **xMin (log)** `= max(min(vals > 0) * 0.7, 1e-6)`. In linear mode xMin is 0.
- **x(v)**:
  - log: `X0 + log10(v/xMin) / log10(xMax/xMin) * (X1 - X0)`
  - linear: `X0 + v/xMax * (X1 - X0)`
- **yMin** `= max(0, floor((min(...iq, 30) - 4) / 10) * 10)`. The 30 caps yMin at 20 or below.
- **yMax** `= ceil((max(...iq, 50) + 2) / 5) * 5`, so yMax is at least 55.
- **y(v)** `= Y0 - (v - yMin)/(yMax - yMin) * (Y0 - 30)`

Default data (verified): intelligence ranges 21.5–57.6, giving y = 10..60. Cost ranges $0.0047–$7.63, giving xMin ≈ 0.0033 and xMax ≈ 8.24.

## 4. Ticks, gridlines and axes

Nice-tick helper `nice(lo, hi, n=5)`:

- `raw = (hi-lo)/n || 1`
- `p = 10^floor(log10(raw))`
- `step = (raw/p <= 1 ? 1 : <=2 ? 2 : <=5 ? 5 : 10) * p`
- ticks run from `ceil(lo/step)*step` to `hi` inclusive, adding `step` each time.

The original accumulates floats (`0.6000000000000001`). That is harmless for display but should not be used as a key.

- **Y ticks** = `nice(yMin, yMax)`. For each tick, a `<g transform="translate(0, y(t))">` contains:
  - a gridline `x1=X0 x2=X1`, stroke `var(--line)`, `stroke-dasharray="2 6"`, width 1. This is the only gridline type.
  - a label at `x = X0-17`, `y = 4`, `text-anchor=end`, fill `var(--fg-3)`, size `12v`. The text is the raw number (e.g. "60"). The verified desktop label x is 47.
- **X ticks (log)**: for each decade `10^e` with `e` from -5 to 4, multiply by these mantissas:
  - if `log10(xMax/xMin) < 1.5` (narrow range): desktop `[1, 1.5, 2, 3, 5, 7]`, compact `[1, 2, 5]`
  - otherwise: desktop `[1, 2, 5]`, compact `[1, 3]`

  Keep the products that lie in `[xMin, xMax]`. Default desktop ticks: $0.005, $0.01, $0.02, $0.05, $0.1, $0.2, $0.5, $1, $2, $5. Mobile ticks: $0.01, $0.03, $0.1, $0.3, $1, $3 (verified).
- **X ticks (linear)** = `nice(0, xMax)`. Default: $0, $2, $4, $6, $8 (verified).
- Each x tick is a `<g transform="translate(x(t), Y0)">` holding a tick mark `<line y2=5 stroke=var(--line-2)>` that points down 5 px, and a label at `y=26`, `text-anchor=middle`, fill `var(--fg-3)`, size `12v`, text `fmt(t, metric, short=true)`.
- X axis line: `X0..X1` at `Y0`, stroke `var(--line-2)`. There is no y-axis line and there are no vertical gridlines.
- Y title: "Intelligence index" at `(X0, 18)`, start anchor, fill `var(--fg-2)`, `12v`.
- X title: `"{label} ({unit}{', log scale' if log})"` at `((X0+X1)/2, Y0+57 | +40)`, middle anchor, fill `var(--fg-2)`. Examples:
  - cost: "Cost per task (USD, log scale)" or "Cost per task (USD)"
  - time: "Time per task (lower is better, log scale)" (their `Wt.time.unit` really is "lower is better")

Color aliases (`Xn`):

| alias | value |
|---|---|
| grid | `var(--line)` |
| axis | `var(--line-2)` |
| tick | `var(--fg-3)` |
| title | `var(--fg-2)` |
| value | `var(--fg)` |
| hover | `var(--hover)` |

## 5. SVG paint order (DOM order)

1. background rect
2. y-axis title
3. y gridlines and labels
4. x ticks
5. x-axis line
6. Pareto path (when on)
7. one `<g>` per family (series path, then that family's points)
8. right-side labels (leader path and label group per family)
9. x-axis title
10. crosshair overlay group (`pointer-events:none; aria-hidden`), always on top

Families are ordered by first appearance in `O`, i.e. dataset order. The default order is Fable, Haiku, Opus, Gemini 4 Argon, GPT-6.1 Sol, GPT-6 Astra, GPT-6 Luna, Grok 4.7, so later families paint over earlier ones. An active point is not raised to the top.

## 6. Series, points and dimming

### Derived state

- `pinned` (A): the clicked or tapped model, or null. Local to the chart.
- `hovered` (H): the model under the pointer or keyboard focus, or null. Local to the chart.
- `labelHover` (T): the family whose right label is hovered or focused. Local to the chart.
- `highlights` (M): array of family ids. App-level and shared by all charts. Toggled by label click, the context menu and mobile legend buttons.
- `focusFamily` (d): the family of the sidebar row under a mouse pointer (`pointerType === 'mouse'`) or with `:focus-visible`. App-level.
- `active` (J) = `H ?? A`.
- `comparing` = `A && H && A.id !== H.id`.
- `pareto` (k) = scatter and `frontier` state on.
  - `paretoIds` = ids of `paretoSet(O)` (§10)
  - `paretoFams` = families of those ids
- `focus` (le) = `(labels && T) || d || (compact ? A?.family : null)`, kept only if some row in `O` has that family.
- `anyEmph` (ue) = `O.some(r => M.has(r.family)) || !!focus`.
- `emph(f)` (de) = `M.has(f) || f === focus`.

### Family series `<g>`

- Group opacity is `0.15` when `!pareto && anyEmph && !emph(f)`, otherwise `1`.
- The path is `M x,y L x,y …` through the family's rows sorted by `effortOrder` ascending. This is effort order, not x order. A single-point family produces a path that draws nothing.
  - `fill: none`
  - stroke: the color of the family's first row (§13)
  - `stroke-width` = `emph ? 3.5 : 2.25`
  - opacity:
    - Pareto on: `emph ? .6 : paretoFams.has(f) ? .25 : .08`
    - Pareto off: `emph ? 1 : .8`
  - `stroke-dasharray="5 5"` if the family's first row (lowest effortOrder) is `deprecated`
  - default linecap and linejoin

### Point (one `<g>` per row, after the path)

- Attributes: `role=button`, `tabindex=0`, `aria-pressed=(A is row)`, `data-active`, `cursor:pointer`.
- `aria-label`: `"{name}, {effortLabel}, Cost per task {fmt(cost)}, intelligence {fmt(iq)}"`.
- Desktop only: `pointer-events` stays normal. On compact the group gets `pointer-events:none`.
- Hit area: `<circle r=13 fill=transparent>`.
- Visible circle:
  - radius: `7` if the row is active or pinned, else `6` if it is in paretoIds, else `4.5`
  - fill: family color
  - stroke: `var(--fg)` width 1.5 if in paretoIds, else `var(--bg)` width 1.8. The bg-colored ring makes points look cut out of the line.
- Group opacity `pe(row)`:
  - Pareto on: `1` if in paretoIds, or the row is J or A; else `.15`
  - else if `anyEmph`, or there is no J, or the row is J or A: `1`
  - else `.45`. While hovering or pinned without highlights, every other point fades to .45 and lines stay as they are (verified in screenshot 03).

### Interaction on points

- `mouseenter` and `focus` set H to the row. `mouseleave` and `blur` set H to null.
- `click` toggles the pin: if A is this row, unpin, else `A = row`. It also clears H.
- `keydown Enter` or `Space` calls `preventDefault` and toggles the pin. `Escape` unpins.
- `contextmenu` opens the app context menu for this model (§12).
- Points have no focus ring: `.chart-svg g[role=button]:focus{outline:none}`. Focus shows up as the hover state instead: 7 px radius, crosshair and tooltip.

## 7. Right-side labels (desktop, scatter, `labels` on)

1. **Families**: take one entry per family in `O`.
2. **Anchor variant**: the family's row with the highest `intelligence`. A reduce over rows sorted by effortOrder replaces the anchor only on a strictly greater value, so ties keep the lowest effortOrder.
3. **Selection**: sort entries by `y(anchor.intelligence)` ascending (top of chart first; ties keep order) and keep the first `S` (at most 16). Lower families are not labelled at all: no leader and no label. Compact mode keeps every family.
4. **Spacing**: `prev = 6`. For each entry in order, `ly = max(y(anchor.iq), prev + 24)` and then `prev = ly`. The first label therefore sits at y ≥ 30, and consecutive labels are at least 24 px apart. There is one downward pass only.
5. **Overflow**: if the last `ly > Y0`, shift every label up by `(last − Y0)`. Nothing is clamped at the top.
6. **Leader line**: drawn before each label, with `pointer-events:none`.
   - path `M (px+6) py L (X1+18) ly L (X1+20) ly`, where (px, py) is the anchor point
   - stroke = family color, width 0.75, opacity 0.22
   - never dimmed
7. **Label group**: `class="series-label"`, `transform="translate(X1, ly)"`, `role=button`, `tabindex=0`, `aria-pressed=M.has(f)`, `aria-label="Highlight {name}"`.
   - Hit rect: `x=24, y=-12, width=W-X1-24` (211 on desktop), `height=24`, transparent.
   - Logo (if the lab has one): `<image x=27 y=-9 width=18 height=18>`. It gets class `monochrome-logo` for the labs openai, anthropic, xai, kimi and zai.
   - Text at `x = 53` (27 without a logo), `y=4`:
     - fill = family color
     - size `13v`
     - weight `700` if `paretoFams.has(f)`, else `550`
     - text = `name.replace('Claude ', '')`. This removes the first occurrence only, giving "Opus 5.5" and "Fable 5.1".
   - Group opacity:
     - Pareto on: `paretoFams.has(f) ? 1 : .2`
     - else: `anyEmph && !emph(f) ? .4 : 1`
   - Events:
     - `mouseenter` and `focus` set T to the family; `mouseleave` and `blur` clear it. This gives a temporary emphasis.
     - `click`, `Enter` and `Space` toggle the family in `highlights`.
     - `contextmenu` opens the menu for the anchor model.
8. **Verified geometry** (desktop, Y0=681): label y positions are Opus 117, Fable 172, Astra 196 (pushed down from 181), Argon 220, Sol 244, Grok 268, Haiku 301, Luna 370.

Lab logos are embedded SVG data URIs for openai, anthropic, google, xai, meta, kimi, zai, deepseek and xiaomi. The monochrome ones are drawn white and inverted in the light theme through `filter: var(--logo-filter)`.

HTML contexts use a fallback when a lab has no logo: a `span.lab-monogram` showing the first letter of `labName`, `font-size: size*.55`, `background: var(--hover)`, `color: var(--fg-2)`, `border-radius: 3px`, weight 600. The SVG labels have no monogram; the text simply starts at x=27.

**Mobile legend** (compact, scatter, labels on, O non-empty): an HTML `.chart-legend` is placed below the SVG.

- Layout: a two-column grid, `gap 2px 12px`, `padding-top 10px`.
- One button per entry, in the same top-to-bottom order.
- Each button: 13 px lab logo plus stripped name, `color` = family color, 13 px, weight 550, `min-height: 32px`, `gap: 7px`, `nowrap`, `overflow: hidden`.
- `aria-pressed = highlighted`. Class `dim` (opacity .35) when `anyEmph && !emph(f)`.
- Click toggles the highlight.

## 8. Hover and pin crosshairs (overlay group)

Models drawn: if A exists, `[A]` plus H when comparing. Otherwise `[H]` if hovering. The pinned model is drawn first. `solid = (model is A)`.

For each model at point (px, py):

- **Horizontal line**:
  - from `X0` to `X1` (the whole plot width) at `py`
  - stroke = family color, `stroke-opacity .8`, width 1
  - solid when pinned, `dasharray "4 4"` otherwise
- **Intelligence value label**:
  - at `(X0+6, py-7)`
  - fill = family color, size `11v`
  - halo: `stroke var(--bg)`, `stroke-width 3`, `paint-order: stroke`
  - text `fmt(iq,'intelligence')`, e.g. "57.6"
- **Vertical line**:
  - `x=px`, from `y=30` down to `Y0`
  - stroke = family color, `stroke-opacity .5`, width 1
  - solid when pinned, else `"4 4"`
- **Metric value label**:
  - at `(min(px+6, X1-60), Y0-8)`
  - same style and halo as the intelligence label
  - text `fmt(value, metric)` in long form, e.g. "$5.98"

## 9. Tooltip panel (HTML, sibling of the canvas inside `.chart-wrap`)

The panel renders when J exists (hovered, otherwise pinned).

Classes: `chart-tooltip scatter-tooltip` plus `pinned` when A exists and `comparing` when comparing. `role="status"`.

**Position and size (desktop)**:

- `position:absolute; right:8px; bottom:72px` (scatter). The bar chart variant uses `top:28px; left:8px`.
- `width:272px`, or `400px` when comparing. `max-width: calc(100vw - 48px)`.
- `padding:14px 16px`, `background: var(--surface)`, `border: 1px solid var(--line-2)`, `border-radius:8px`, `z-index:3`.
- `pointer-events:none`, except that in `.pinned` the close button and the link accept events.
- There are no transitions.

**Mobile (≤900px)**:

- `position: sticky; bottom: calc(10px + env(safe-area-inset-bottom)); z-index:7; width:auto; margin-top:14px`. It sits below the legend, inside the flow.
- When not comparing it is a grid of `1fr 1fr` with `column-gap 20px` and `padding 12px 14px`. Value rows pair up two per line, and every non-value child spans both columns.
- `p` gets `margin-bottom: 6px`, and the link `margin-top: 6px`.

**Rows, in order**:

1. **Head** `.tooltip-head`: a flex row with space-between, gap 12, 13 px.
   - `strong` (inline-flex, gap 8, weight 550): the 18 px lab logo, then `<span style="color: familyColor">{J.name}</span>`. This is the full name, e.g. "Claude Opus 5.5".
   - A close button (20×20, color `--fg-3`, lucide `x` icon at 14 px, `aria-label="Close details"`) that clears both A and H.
2. **`p`** (`--fg-2`, 11.5 px, margin `4px 0 12px`): `{J.effortLabel}`, followed by `" · Pinned"` when J is A. Example: "max · Pinned".
3. **Not comparing**: one `.tooltip-value` per metric. Each is a flex row with space-between, gap 20, `padding 4px 0`, 12 px. The label span is `--fg-2` and the value `b` is weight 500 with tabular-nums.

   Metric list: `[intelligence, metric, …(metric==='cost' ? [tokens, time] : [cost])]`, deduplicated. For this chart that gives:
   - Intelligence index: 57.6
   - Cost per task: $5.98
   - Tokens per task: 119.2k
   - Time per task: 13m 4s

   (verified)
4. **Comparing**:
   - `.comparison-reference` (`--fg-2`, 11.5 px, gap 7, mb 8): the pinned model's 14 px logo, then `"vs {A.name} · {A.effortLabel}"`.
   - `table.comparison-table`: 11.5 px, right-aligned, tabular-nums.
     - thead (`--fg-3`, 11 px, `border-bottom 1px var(--line-2)`): an sr-only "Metric" cell, then "Selected", "Hovered", "Multiplier".
     - Body rows: `th` = metric label (left-aligned, `--fg-2`), then `fmt(A[m])`, `fmt(H[m])` and `mult(H[m], A[m])`. The last column has weight 550.
     - Cells: `padding: 4px 0 4px 12px`.
5. **Link**: `<a href="https://artificialanalysis.ai/models/{id}" target=_blank rel=noreferrer>Artificial Analysis</a>`. Color `--accent`, underline with offset 3, 11.5 px, `margin-top: 10px`.

**Formatter `fmt(v, metric, short=false)`**:

- `null` → `"—"`.
- **time, short**: below 60 s show seconds, below 3600 s minutes, otherwise hours. Format `value/unit` with up to one decimal and the suffix `s`/`m`/`h`, e.g. "1.5m", "13.1m", "2h".
- **time, long**:
  - below 60 s: `"{v, max 1 decimal}s"`, e.g. "45.3s". Note that 59.96 gives "60s".
  - otherwise `s = round(v)`: if `s < 3600`, `"{floor(s/60)}m {s%60}s"` ("13m 4s"), else `"{h}h {m}m"` ("1h 2m").
- **cost and costTotal**:
  - short and ≥1000: `"$" + (v/1000).toFixed(1).replace(/\.0$/,'') + "k"` ("$1.2k").
  - else `"$" + v.toLocaleString('en-US', {maximumFractionDigits: costTotal ? 0 : v<1 ? 3 : 2, minimumFractionDigits: (metric==='cost' && !short) ? 2 : 0})`.
  - Examples:
    - long: `$5.98`, `$0.10`, `$0.119`, `$1,234.50`; `$0.0004` gives `$0.00`
    - short: `$0.005`, `$0.1`, `$0`, `$8`
    - costTotal: `$233`
- **Everything else** (intelligence, tokens):
  - ≥1e9 → `x.xB`; ≥1e6 → `x.xM`; ≥1e3 → `(v/1e3).toFixed(short?0:1)` with `.0` stripped, plus `k` ("119.2k" long, "119k" short, "120k" for 120020)
  - else `toLocaleString` with max decimals 1 for intelligence, `short?0:1` otherwise ("57.6", "50").
- **Multiplier** `mult(a, b)`: `"—"` if either value is null or `b === 0`. Otherwise `(a/b).toLocaleString('en-US', {maximumSignificantDigits: 3}) + "×"`, e.g. "0.914×", "0.545×", "1,500×". The direction is hovered ÷ pinned.

## 10. Pareto ("Pareto line")

- `better` per metric: lower for cost, time, tokens, tokensTotal and costTotal; higher for speed and intelligence. Let `dir = lower ? 1 : -1`.
- `paretoSet(O)`:
  1. Keep rows with non-null metric and intelligence.
  2. Sort by `(a[m]-b[m])*dir`. Ties sort by intelligence descending.
  3. Walk the sorted list and keep a row only when `intelligence > runningMax`, a strict increase, then update `runningMax`.
- This uses the visible set only: selected families, non-excluded efforts, and non-positive values dropped in log mode.
- Path: `M…L…` through the kept rows in sorted order. Segments are straight, not steps, so two points at nearly the same cost show as a near-vertical segment (verified).
  - stroke `var(--fg)`, width 2.5, `dasharray "6 5"`, opacity .95, `pointer-events:none`
  - drawn under the series groups
- Emphasis while on:
  - Pareto points: r=6, stroke `var(--fg)` 1.5, opacity 1. Other points: opacity .15, except the active or pinned point.
  - Lines: highlighted .6, families with at least one Pareto member .25, the rest .08. Family groups are never faded.
  - Labels: families with Pareto members get opacity 1 and weight 700, the rest opacity .2 and weight 550.
  - Sidebar: when `frontier` is on, a selected `.model-row` gets `.on-frontier` (weight 550) or `.off-frontier` (opacity .35, back to 1 on hover or focus-visible).
- Control: `button.pareto-toggle[aria-pressed]`, `title="Show non-dominated variants: no other visible variant is both better and cheaper or faster."`. Its content is a `span.selection` checkbox (12×12, `1px var(--line-2)` border, radius 3; when checked the background and border are `--accent` and it shows a lucide `check` at 11 px, stroke-width 3, color `--on-accent`) followed by the text "Pareto line".
  - CSS: `min-height 32px`, `color var(--fg)`, gap 8, 12 px, nowrap. Pressed or hover: `color var(--accent)`. Mobile: `min-height 44px`.
  - The `frontier` flag is one app-wide setting shared by both scatter charts, URL `?frontier=true`.

## 11. Keyboard, mouse and touch

- **Tab order**: every point (by family in DOM order, then by effortOrder), then every right label. All have `tabindex=0`.
  - Focus on a point acts as hover.
  - Enter or Space on a point toggles the pin; Escape on a point unpins.
  - Enter or Space on a label toggles the highlight.
- **Global Escape**: each chart adds a `window` keydown listener that clears the pin, hover, label hover and all highlights. The app's own listener also closes the mobile sheet and the settings popover. `/` focuses the model search.
- **Desktop click** on empty chart space does nothing; the pin stays. Unpin by clicking the pinned point, pressing the close button or pressing Escape.
- **Mobile tap**:
  - Points ignore pointer events, so the SVG's `click` handler converts `clientX/clientY` to SVG coordinates with `getScreenCTM().inverse()`.
  - It finds the nearest row in `O` by Euclidean distance in SVG units, which equal CSS px. Dimmed points count too.
  - It clears H. If the distance is below 40 it sets A to that row, otherwise it unpins.
  - Tapping the same point again keeps it pinned; this is not a toggle.
  - On compact, the pinned family becomes `focus`: its line width goes to 3.5, other families fade to .15 and other legend buttons get `.dim`.
  - Hover is impossible on mobile, so comparing never happens there in practice.

## 12. Right-click context menu (app level, shared)

- **Openers**:
  - Right-click on empty SVG space: no model.
  - Right-click on a point or label: that model; a label passes its anchor variant.
  - Right-click on a sidebar row.
  - The handler calls `preventDefault` and `stopPropagation`. Its position is `clientX/clientY`; when the event comes from the keyboard and those are 0, it uses the target's `rect.left/rect.bottom` instead.
- **Title** (`.context-menu-title`, color `--accent`, padding 8): `model.name` (e.g. "GPT-6 Astra"), otherwise the lab name, otherwise "Chart".
- **Definitions**:
  - "listed families" (Oe): the families shown in the sidebar, in sidebar order. That is the Frontier list, the Notable list, then the "Other" families that are visible because they are selected, match a search, or pass the "Show all models" filters.
  - "LabName": the `Bt` name (OpenAI, Anthropic, Google, xAI, Meta, Kimi, Z AI, DeepSeek, Xiaomi), otherwise the data's `labName`, otherwise the lab id.
- **Model items**, shown only when the menu has a model:
  1. "Hide this family" or "Show this family", depending on whether the family is selected: toggles the family in `selected`.
  2. "Show only this family": `selected = [family]`.
  3. "Show all except this family": `selected = listedFamilies − family`.
  4. "Highlight this family" or "Unhighlight this family": toggles the family in `highlights`.
- **Lab items**, shown when there is a lab (`model.lab` or a lab-only opener). The first of them gets the divider class when model items come before it.
  1. "Show all {LabName}": `selected ∪ listed families of that lab`.
  2. "Hide {LabName}": removes from `selected` every family whose lab matches, across all families in the dataset.
  3. "Show only {LabName}": `selected = listed families of that lab`.
  4. "Show all except {LabName}": `selected = listed families of other labs`.
- **General items** (always). The first carries the divider class even when it is the first item.
  1. "Show all listed models": `selected = listedFamilies`.
  2. "Reset model selection": `selected = default`.
  3. "Clear model selection": `selected = []`.
  4. "Clear highlights": only when highlights is non-empty; `highlights = []`.
- **Behaviour**:
  - `role=menu`, `aria-label=title`.
  - After layout the menu is clamped to `[8, innerWidth − width − 8]` × `[8, innerHeight − height − 8]`, and the first button gets focus.
  - It closes on a pointerdown outside, on window resize, on a scroll outside (capture phase) and on Escape or Tab (with stopPropagation).
  - ArrowDown and ArrowUp move focus with wrap-around; Home and End jump to the ends.
  - Clicking an item runs it and closes the menu. Closing returns focus to the element that opened the menu.
  - Right-clicking the menu itself is ignored.
- **CSS**:
  - `position: fixed`, `z-index: 100`, `width: 250px`, `max-width: calc(100vw - 16px)`, `max-height: calc(100dvh - 16px)`, `overflow-y: auto`.
  - `background: var(--surface)`, `border: 1px solid var(--line-2)`, `radius 8`, `padding 6`, 12 px.
  - Items: `display: block`, full width, left-aligned, `color --fg-2`, `radius 5`, `padding 8`. Hover and focus: `background --hover`, `color --fg`, no outline.
  - `.menu-divider`: `border-top: 1px solid var(--line-2)`, `border-radius: 0`, `margin-top: 5px`.

## 13. Colors

### Theme variables

The theme is set by `:root[data-theme]`. Dark is the default and is not persisted. `meta theme-color` is `#000000` in dark and `#ffffff` in light.

| var | dark | light |
|---|---|---|
| `--bg` | `#000` | `#fff` |
| `--fg` | `#fff` | `#20201e` |
| `--fg-2` | `#aaa39d` | `#625d57` |
| `--fg-3` | `#77716c` | `#77716c` |
| `--line` | `#1c1a18` | `#e8e4df` |
| `--line-2` | `#36312d` | `#ccc5be` |
| `--surface` | `#0d0b0a` | `#f8f6f3` |
| `--hover` | `#141210` | `#f1eeea` |
| `--accent` | `#c5ac98` | `#806047` |
| `--on-accent` | `#000` | `#fff` |
| `--logo-filter` | `none` | `invert(1)` |
| `color-scheme` | `dark` | `light` |

Other root settings: `--sidebar-width: 248px`, `--header-height: 60px`, `font-family: DM Sans, sans-serif`, `body { user-select: none }`. Focus ring: `outline: 2px solid var(--accent); outline-offset: 3px`. `::selection` uses `--accent` on `--on-accent`. Disabled buttons get opacity .4.

### Family colors

Colors are resolved by `color(row)`, which tries, in order:

1. `FRONTIER[family]`
2. `NOTABLE[family]`
3. the `LAB[row.lab]` color
4. `light-dark(#637082, #a4adb9)`

The color always comes from the row's own family and lab; the bundle has no per-variant shading on the scatter chart.

Frontier families (`L`). The sidebar tier buttons Small, Medium and Large toggle all families of a tier.

| family | tier | light | dark |
|---|---|---|---|
| gpt-6-astra | Large | `#303840` | `#f1f3f5` |
| gpt-6-1-sol | Medium | `#586878` | `#c5cbd3` |
| gpt-6-luna | Small | `#748292` | `#939daa` |
| claude-opus-5-5 | Large | `#ae5235` | `#df9477` |
| claude-fable-5-1 | Large | `#903e2b` | `#cc785c` |
| claude-sonnet-5-5 | Medium | `#bd6948` | `#f0b99f` |
| claude-haiku-5-5 | Small | `#c4805f` | `#b98a74` |
| gemini-4-argon | Large | `#218347` | `#56ca80` |
| gemini-3-8-flash | Medium | `#247a3c` | `#34a853` |
| grok-4-7 | Large | `#6d55bd` | `#9b94ee` |

The light-theme Fable fill measured `rgb(144,62,43)` = `#903e2b`, which matches.

Notable families (`Rt`):

| family | light | dark |
|---|---|---|
| mimo-v2-6-pro | `#b85212` | `#ff8b45` |
| muse-spark-1-3 | `#236bbd` | `#5ea4ff` |
| kimi-k3 | `#ab3f83` | `#ee86c4` |
| glm-5-3 | `#8e7318` | `#ecd36e` |
| glm-5-3-flash | `#7c6b2e` | `#b9a453` |
| deepseek-v4-pro | `#157d83` | `#52cdd2` |
| deepseek-v4-1-flash | `#216b70` | `#33979c` |

Lab fallbacks (`Bt`). This list also sets the sidebar's lab sort order and the context-menu lab names.

| lab id | name | light | dark |
|---|---|---|---|
| openai | OpenAI | `#303840` | `#f1f3f5` |
| anthropic | Anthropic | `#ae5235` | `#df9477` |
| google | Google | `#218347` | `#56ca80` |
| xai | xAI | `#6d55bd` | `#9b94ee` |
| meta | Meta | `#236bbd` | `#5ea4ff` |
| kimi | Kimi | `#ab3f83` | `#ee86c4` |
| zai | Z AI | `#8e7318` | `#ecd36e` |
| deepseek | DeepSeek | `#157d83` | `#52cdd2` |
| xiaomi | Xiaomi | `#b85212` | `#ff8b45` |
| any other | — | `#637082` | `#a4adb9` |

Other colors in the bundle, outside this chart:

- Usage-page harness fallbacks: opencode `#7951b4`/`#c9a2ff`, cursor `#8e701d`/`#f1d185`, pi `#247b8c`/`#88d8e7`, devin `#667d2e`/`#b7c984`, githubCopilot `#93549e`/`#da9de6`, other `#77716c`.
- Neutral: `light-dark(#625d57, #aaa39d)`. Mixed models: `light-dark(#776253, #b9a89b)`.

Colors are written as `light-dark(light, dark)` strings directly into SVG `fill`/`stroke` attributes and inline `style.color`, and resolve through `color-scheme`. A vanilla reimplementation should either set them as CSS properties (`style.stroke = …`, safest across browsers, Firefox included) or pick the hex for the current theme in JS.

## 14. Controls around the chart (placement)

**Section** (`.chart-section`, one per view, scroll-snapped feed):

- Desktop: `height: 100%`, `padding: 18px 28px 10px` (18 px sides at ≤1150px).
- Mobile: `padding: 20px 16px 24px`, `scroll-margin-top: 95px`.

**Heading row** (`.chart-heading`): flex, space-between, align center, gap 16, `margin-bottom: 6px`.

- Left: `h2` "Cost vs intelligence", 16 px, weight 500; 18 px on mobile.
- Right: `.chart-controls` (flex, gap 24) holds the Pareto toggle, then `.chart-scale`.
- `.chart-scale` is a `role=group`, `aria-label="Cost vs intelligence axis scale"`, gap 12 (10 on mobile). It contains two buttons in the order "Linear", "Log", each with `aria-pressed` for the current mode.
  - Button CSS: `min-height: 32px` (44 on mobile), `padding: 4px 2px`, 12 px, `color: --fg-3`, `border-bottom: 1px solid transparent`.
  - Pressed: `color` and `border-color` `--accent`, which draws an underline. Hover: `--fg`.
- Mobile: `.chart-heading` wraps (gap `4px 16px`) and `.chart-controls` takes the full width with space-between, so Pareto sits left and Linear/Log right.
- Scale state is per view: the `linear` array holds the view ids that are in linear mode.

**Settings popover**: the header button is `details.chart-settings` with a lucide `ellipsis` icon, desktop only. On mobile the same controls appear in the sheet under "Charts".

- Popover: `--surface`, `1px --line-2` border, radius 8, width 220, padding 16, `top: calc(100% + 10px)`, right 0, z 20.
- Contents:
  - "2D charts": a "Labels" check-button.
  - "Bar charts": "Group by model" and "Highest first"/"Highest last".
  - "Reset highlights", shown only when highlights exist.

**Empty state** (`O` empty): a centered `.empty` block (gap 10).

- A `strong` (17 px, weight 500) shows one of:
  - "No models selected" (selection empty)
  - "No reasoning levels enabled" (rows empty)
  - "No data for this view"
- Below it, `button.text-button` "Reset filters" (accent, 12 px). It resets selection, search, browse toggles, highlights and the context menu, and remounts the charts.

## 15. PNG export (header download button)

The button is `.icon-button.desktop-only` (32×32, `--fg-2`) with a lucide `download` icon at 15 px. Its `title` and `aria-label` are "Download PNG", or "PNG download failed. Try again" after an error. It is disabled while exporting or when the active view has no data. It exports the active view, i.e. the tab or section currently scrolled into view.

Steps:

1. Find `svg#chart-{viewId}`, deep-clone it, and walk the original and the clone in parallel.
2. For every element, copy these computed styles onto the clone as attributes, which resolves `var()` and `light-dark()`: `fill`, `fill-opacity`, `stroke`, `stroke-width`, `stroke-opacity`, `stroke-dasharray`, `font-family`, `font-size`, `font-weight`, `text-anchor`, `dominant-baseline`, `opacity`, `filter`.
3. `w×h` = viewBox size. On the clone set `y=44`, `width=w`, `height=h` and remove its `style`.
4. Build a wrapper `<svg xmlns viewBox="0 0 w h+44" width=w height=h+44 font-family="Arial, sans-serif">` containing:
   - a full-size `<rect>` filled with the `<html>` computed `background-color`
   - a title `<text x=24 y=30 font-size=18 fill=<html color>>` holding the view label ("Cost vs intelligence")
   - the clone
5. Serialize the wrapper to a Blob URL, then load it into an `Image()` and `await decode()`.
6. Create a canvas of `ceil(2w) × ceil(2(h+44))` and `drawImage` the image scaled to fill it. This 2× raster also captures the current hover, pin and dimming state.
7. Call `toBlob('image/png')` and download through an `<a>` with `download="slopalytics-cost-intelligence.png"`. Revoke the URLs afterwards (the PNG URL after 30 s).

Logos are data URIs, so they survive the export. DM Sans is not available inside the image, so text falls back to a system font. The HTML tooltip and legend are not included.

## 16. Implementation notes for our vanilla version

- Field mapping to our `models.json` is covered in `/tmp/claude-1002/slopalytics-facts/mapping.md`.
- Rendering happens on every state change. A single `render()` that rebuilds the SVG from state (pinned, hovered, labelHover, highlights, focusFamily, pareto, log, theme, size) reproduces their behaviour exactly, because nothing is animated: there are no transitions anywhere in the CSS.
- Keep hover and pin local to each chart. Keep highlights and frontier global, and keep linear per view.
- Use integer-index tick generation (`start + i*step`) to avoid float drift.

---

## Appendix A: lucide icons used

- `x` (close)
- `check` (checkbox)
- `download`
- `ellipsis` (settings)
- `sun` / `moon` (theme)
- `rotate-ccw` (reset)
- `search`
- `sliders-horizontal` (mobile filter)
- `arrow-down` (sort)

All are 24-unit viewBox strokes: `stroke=currentColor`, width 2, round caps and joins.

## Appendix B: bar mode of the same component (other views)

- Bar groups are built by grouping rows by family (grouped) or by id. Groups are sorted by their max value, ascending or descending.
- Geometry:
  - baseline `Cb = H − (grouped ? 96 : 128)`, right edge `W − 18`
  - scale `y(v) = Cb − v/max*(Cb−30)` with `max = 1.15 × maxValue`
  - y ticks `nice(0, max)`, labels `11v` at `X0−10`, gridlines `2 6`
- Group width is proportional to `max(3, rows)`. `gap = min(4, groupW*.025)` and `barW = clamp(1, 38, (groupW−16)/rows − gap)`.
- Bars use `rx 4` with opacity `.62 + .38*effortOrder/60`. Hover and active bars get a `var(--hover)` column behind them.
- Value labels are `11v` with a halo, stacked upward by `17v` to avoid collisions (label width ≈ `chars*6.4*v`). A leader line (opacity .3) connects a label that has moved more than 10 px.
- Grouped mode labels each bar with an effort letter: N, L, M, H, X, Mx, D.
- Group label:
  - grouped: a 20 px logo plus wrapped name, 11v, weight 550
  - otherwise: a 16 px logo plus `rotate(-55)` text "{name} · {effort letter}"
- Mobile replaces bars with an HTML dot plot.
