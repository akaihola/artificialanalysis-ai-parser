# Rebuild the cost vs intelligence chart in the style of slopalytics.com

Adopt the UI, UX and functionality of the "Cost vs intelligence" graph on
<https://slopalytics.com/>: graph style, colours, indicators, Pareto line, model and
reasoning selectors, model search, hover details and other UX. Keep our own scraper, the
speed (max response time) filter slider, the benchmark selector, and the API vs
subscription plan selection for Codex and Claude Code. Work and test in a worktree
branch.

Research and specs, written from slopalytics' public bundle and our data on 2026-10-11:

- [chart-spec.md](../research/slopalytics/chart-spec.md): chart component (geometry,
  scales, ticks, series, labels, crosshairs, tooltip, pin/compare, Pareto, keyboard,
  context menu, PNG export, colours).
- [sidebar-spec.md](../research/slopalytics/sidebar-spec.md): app shell, header,
  sidebar, search, reasoning toggles, curated lists, URL state, theme, mobile.
- [aa-payload.md](../research/slopalytics/aa-payload.md): fields available in the
  Artificial Analysis payloads our scraper already downloads, with key paths.
- [mapping.md](../research/slopalytics/mapping.md): how our models map to their
  families and effort levels.
- [logos.md](../research/slopalytics/logos.md): lab logo sources and licences.
- [critique.md](../research/slopalytics/critique.md): cross-check of the above,
  conflicts with our features.

Screenshots and the extracted bundle were kept out of the repository
(`/tmp/claude-1002/slopalytics-research/` during the session).

## Decisions

### Approach

- Reimplement in our own code. Slopalytics publishes no licence, so do not copy its
  code, CSS or assets; use the specs for behaviour and constants.
- Replace `intelligence-vs-cost.html` in place. It stays one vanilla HTML file with
  hand-written SVG and no build step.
- Branch `feature/slopalytics-cost-chart` in worktree
  `.claude/worktrees/slopalytics-cost-chart`, based on `master` after merging
  `origin/master`.

### Scraper and data

- Extend the scraper with fields from payloads it already fetches: `family` (AA
  `releaseSlug`), `family_name`, `lab` (creator slug), `lab_name`, `released`,
  `effort` and `effort_order`. Add them to the `--minimal` field list so the daily job
  keeps them.
- Parse `effort` from the AA model name: minimal/low/medium/high/xhigh/max (optionally
  "with fallback"), "Non-reasoning" gives `none`, otherwise `default` (order 35) for
  reasoning models and `none` (order 0) for the rest. Orders: none 0, minimal 10, low
  20, medium 30, default 35, high 40, xhigh 50, max 60.
- Use AA's model-level cost per task and model-level median e2e response time: one
  point per model variant, like slopalytics. The host is not shown in the UI.
- Plans apply by lab: Anthropic models get the Claude plan; OpenAI models that are not
  open-weights get the Codex plan (gpt-oss stays at API price).
- Do not fetch AA model pages (tokens per task and time per task are not collected).
- Models with zero price stay excluded, as before.

### Page layout

- Slopalytics layout: 60px header, chart area, 248px right sidebar, footer, DM Sans
  from Google Fonts with a `system-ui` fallback.
- Header: our page title in their wordmark style; our benchmark selector as header tabs
  in their chart-tab style (Intelligence, Coding (SciCode), Math (AIME 2025),
  Terminal-Bench v4.0, LiveBench Coding, LiveBench Agentic Coding). No slopalytics
  wordmark, no Benchmarks/Usage tabs, no other chart tabs.
- Header icons on the right: theme toggle, PNG download, fullscreen, table view, "?"
  help, and a "…" settings popover with only Labels and Reset highlights.
- Sidebar: their sections (Models N + reset, search, Reasoning, Frontier with
  Small/Medium/Large tiers, Notable with All, Other behind "Show all models" with
  "Open weights"), plus our Claude plan, Codex plan and max response time slider as
  sections under Reasoning, in their text-toggle style.
- Toolbar above the plot: Pareto line, Log/Linear, Zoom Y to Pareto, Show deprecated.
- Table view replaces the plot area; sidebar filters still apply.
- Help text opens in a popover from the "?" icon.
- Fullscreen covers the whole app (header, chart and sidebar).
- Mobile (≤900px) as slopalytics: sticky header, "Models N" sheet (also holding the plan
  selectors and slider), two-column legend under the chart, tap nearest point within
  40px, sticky tooltip card.

### Chart

- Copy their family polylines through effort variants, right-side family labels,
  crosshairs, dimming and highlight rules, fixed tooltip panel, pin-to-compare with
  multipliers, right-click context menu (also on long-press for touch), keyboard
  handling, PNG export and Log/Linear toggle.
- Pareto line in their style (straight dashed segments in `--fg`, emphasis rules), but
  on by default. URL stores `frontier=false` only when turned off.
- Zoom Y to Pareto is disabled unless the Pareto line is on, and ignores their fixed
  30/50 Y clamps.
- Y axis title, crosshair label, label anchor (best-scoring variant per family) and the
  Pareto line follow the selected benchmark.
- Axis ranges come from visible points plus the speed-filtered faint points, so axes
  stay still while dragging the slider but adapt to selection, benchmark and plan.
- Models hidden by the speed filter: family-coloured dots at 0.15 opacity, no hover
  target, skipped by family lines, Pareto line and labels. The slider read-out shows
  "≤ N s · K hidden". Models with unknown response time stay visible.
- Tooltip rows: selected benchmark score (with LiveBench provenance under it for
  LiveBench metrics), Cost per task (effective plan cost, plus API cost when it
  differs), Response time, Output speed, Artificial Analysis link. The comparison table
  uses the same rows.
- Costs under $0.01 use 2 significant digits.
- Points are drawn in slug order (case-insensitive), like slopalytics.
- Colours are resolved per theme in JS (not `light-dark()` in SVG attributes).
- PNG file name uses our page name.

### Models, colours and logos

- Copy slopalytics' Frontier (with tiers) and Notable lists, family colours, lab
  colours and default selection (the 8 Frontier families except Sonnet 5.5 and Gemini
  3.8 Flash; reasoning level `none` hidden) into a config block at the top of the
  script.
- When the selected benchmark has fewer than 3 points, show an empty-state hint with a
  "Show models with <benchmark> data" button.
- Lab-wide select/deselect through the context menu ("Show only / Hide <lab>"); no
  visible per-lab checkboxes.
- The sidebar lists only families with at least one variant that has a cost.
- One "Show deprecated" control (toolbar, off by default, `deprecated=true` in the URL).
  Off: deprecated families are hidden from sidebar, search and chart. On: listed and
  drawn dashed. No separate "Older" toggle.
- Logos for the same 9 labs as slopalytics (OpenAI, Anthropic, Google, xAI, Meta, Kimi,
  Z.ai, DeepSeek, Xiaomi), from lobehub/icons (MIT): mono marks where slopalytics uses
  inverted white logos, colour marks for Google, Meta and DeepSeek, Xiaomi from
  simple-icons (CC0) in `#ff6900`. Letter monograms for other labs. MIT notice in the
  footer.

### State

- Theme follows the system setting until the user picks one; the choice is remembered
  in `localStorage`.
- URL uses readable parameters (slopalytics style: `models=<family>,<family>`,
  `hide-reasoning`, `frontier`, `linear`, `labels`) plus `metric`, `claude_plan`,
  `codex_plan`, `max_response_time` and `deprecated`; values equal to defaults are
  omitted. Search text is not stored.
- Old shareable links are not supported: unknown names in `models=` are dropped, and
  if none remain the default selection applies.
- Escape undoes the innermost thing first: context menu or popover, mobile models
  sheet, search text, pin/hover/highlights, fallback fullscreen.

### Tests

- Replace `tests/test_ui.cjs` and `tests/test_firefox.cjs` with Python Playwright tests
  (`unittest`, like `tests/test_parser.py`) running in Firefox and Chromium against a
  local `http.server`, run with `uv run --with <pinned playwright>`. Document this in
  the README.
- Extend the parser tests for the new fields.
- Serve the worktree locally for manual testing.

## Acceptance criteria

- Side by side with slopalytics.com at the same viewport, the chart, sidebar, tooltip,
  Pareto line, search and reasoning selectors look and behave the same, except for the
  decisions above.
- The benchmark tabs, plan selectors, speed slider, table view, fullscreen, show
  deprecated, Zoom Y, LiveBench provenance and theme toggle work.
- URL state round-trips through reload.
- Parser and browser tests pass in Firefox and Chromium.

## Follow-ups

- Fix the scraper's first-party host matching (Alibaba vs Alibaba Cloud, Z AI vs Zai,
  Amazon vs Amazon Bedrock, Microsoft vs Microsoft Azure).
- Refresh the curated Frontier/Notable lists and family colours when new releases
  arrive.
