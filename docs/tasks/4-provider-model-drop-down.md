# Provider and model selection

Tracker: [TASKS.md](../../TASKS.md), issue `[4]`.

## Provenance

This file was never committed. Commit `6c1c79f` added only the `[4]:` link.
The original requirements survived in the prompt of Kandev task
`8c77b371-b5e9-43b7-97db-44ccbcf501f2` ("Condense provider and model
selectors", 2026-09-19). They are quoted below. The recovery section after them
was reconstructed on 2026-09-25.

## Original issue (2026-09-19)

> - [4] Condense provider/model selection into drop-down menus.
>
> Problem: The parser UI currently exposes provider and model selection in a
> more complex form than needed, making the primary selection flow harder to
> use.
>
> Concrete scope: the provider and model selector UI, its existing grouped
> visibility and clear-all behavior, the related state and filtering code, and
> focused frontend tests. Preserve the current provider/model data and selector
> behavior while simplifying the controls.
>
> Acceptance criteria:
> - Provider selection uses a clear drop-down menu.
> - Model selection uses a clear drop-down menu whose choices follow the
>   selected provider.
> - Existing clear-all and grouped visibility behavior remains correct.
> - Add or update focused tests and run the relevant checks.

## Why the first attempt failed

Commits `123184d` and `cd77950` replaced the task [1] checkbox groups with
three controls: a provider `<select>`, a one-row `<select multiple>` of that
provider's models, and a separate search box. This caused four problems:

- Only one provider's models were visible at a time.
- A whole provider could no longer be toggled at once, which broke the
  grouped visibility from task [1].
- Nothing showed how many models were selected.
- A plain click in the list replaced the selection and removed every other
  model of that provider.

## Recovered requirements (2026-09-25)

Build a model picker similar to the Artificial Analysis model selector.

- One compact button shows "Models: N of M selected" and opens a panel.
- The panel has a search box, which gets focus when the panel opens. It
  matches model and provider names and hides providers with no match.
- The panel has "Select all" and "Clear all" buttons. While a search is
  active, both apply only to the matching models. "Clear all" keeps the
  `clear-models` id and semantics.
- Models are grouped by provider, with providers and models sorted. Each
  provider header has a checkbox (checked, unchecked or mixed) and a
  "selected/total" count. Clicking an unchecked or mixed header selects all of
  that provider's models; clicking a checked one clears them.
- Provider groups can be collapsed. They are collapsed by default and
  expanded while a search is active.
- Each model row is one checkbox covering all reasoning levels of that model.
- Escape and clicks outside the panel close it. Escape does not also leave
  full screen.
- The chart and table update on every change. The picker also works in full
  screen mode.

Keep these contracts unchanged:

- The selection is `state.selectedModels`, keyed by `provider::base model
  name`.
- Every model starts selected, and the selection is not stored in the URL.
- Benchmark selection, subscription plans and the response-time filter keep
  their current behaviour.

## Acceptance criteria

- The picker above replaces the provider and model drop-downs.
- Clear-all, provider-level toggles, model-level toggles and benchmark
  selection work correctly.
- `tests/test_ui.cjs` covers the picker. `node --test tests/test_ui.cjs` and
  `python3 -m unittest discover -s tests -v` pass.
