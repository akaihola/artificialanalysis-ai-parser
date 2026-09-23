# Architecture review and ordered remediation plan

Ready for user review. This document authorizes no implementation, deployment, tracker changes, or additional Kandev tasks.

Reviewed on 2026-09-19 at commit `2760b73c8a28b923daf434a74ffc886478f16c5e`. Task `bcc6f211-8e27-4d4e-ad97-f6888d89cd98`, session `225dd421-8cf1-4a8f-aab5-0dcc0e5b05e6`. Kandev confirms Astra Medium and Priority Kanban, with autopilot disabled. The working tree was clean before and after inspection. Repository and tracker files were not changed.

## Architecture and scope

The architecture fits the project: a small, standard-library Python data publisher and a static browser visualization. Keep that shape. The greatest value comes from tightening the published-data contract and verifying the publication path, not adding a backend, database, frontend framework, or generic adapter framework.

All 17 tracked files were inventoried. Both production source files, both test files, the workflow, README, TASKS.md, all three task documents, research document, fixtures, AGENTS.md, and LICENSE were read. The entire generated JSON was parsed and checked programmatically. The local .agents and .codex directories are empty; .claude/skills contains external skill symlinks, not tracked application code. Applicable ancestor guidance and repository AGENTS.md were checked. There is no package manifest, dependency lockfile, separate build system, container configuration, database, or additional tracked script. The research and task documents are the available design records; no separate ADR collection exists.

| Boundary | Responsibility and references | Operational assumptions |
| --- | --- | --- |
| CLI entry | `artificialanalysis.ai-parser.py:360`, `main`; arguments at 362–369 | Python standard library; paths resolve from the current directory; default output is models.json |
| AA acquisition | `fetch_rsc` at 138; endpoints and RSC headers at 25–34 | Two sequential HTTPS requests to undocumented Next.js data streams; 60-second request timeouts; no API key |
| AA extraction and normalization | `extract_rows` at 175; `extract_model_indexes` at 203; `deduplicate_models` at 236; `clean_model` at 285 | Provider rows define price/speed; model arrays provide SciCode, Terminal-Bench, and agentic scores; exact slug joins |
| LiveBench acquisition and join | `fetch_livebench` at 54; `parse_livebench` at 75; mappings at 36–51 | Resolve GitHub main once, download CSV and category JSON at that commit; six reviewed identity/effort mappings; one fixed benchmark release |
| Publication | `main` at 423–475; `compress_for_calculator` at 345 | Filter priced models, check coverage, sort, optionally project fields, write one JSON array; Git provides history |
| Browser loading and state | `intelligence-vs-cost.html:342–413` | Same-origin models.json; no backend; state lives in memory; metric, time limit, and plan choices round-trip through URL parameters |
| Browser computation and rendering | `buildModelFilters` at 422; `effectiveCost` at 372; `paretoFront` at 575; `render` at 600; `showTooltip` at 739; `renderTable` at 772 | One selected provider endpoint per model; optional subscription multiplier; selected score and time filters; SVG plus accessible table |
| Automation | `.github/workflows/update-models.yml:3–39` | Daily 03:17 UTC or manual run, ubuntu-latest, ten-minute job cap, serialized refreshes, direct push to master using checkout credentials |
| Hosting | `README.md:3,203–209` | Local HTTP server or linked GitHub Pages site; actual Pages settings and deployment history are outside the checkout |
| Tests and fixtures | `tests/test_parser.py`, `tests/test_ui.cjs`, `tests/fixtures/*` | Python unittest with mocked acquisition and temporary output; Node VM runs the actual inline browser script against small DOM stubs |

The current snapshot has 411 unique slugs and 315,096 bytes. Non-null metric counts are Intelligence 409, SciCode 158, AIME 173, Terminal-Bench 151, and six each for the LiveBench categories. Browser loading admits 141 rows; the default nondeprecated Intelligence, SciCode, and Terminal-Bench views each have 99 rows. The selector builds 28 provider groups and 100 model checkboxes. All loaded costs are finite and positive. These are measurements of this commit, not permanent thresholds.

### Critical paths traced

1.  **Scheduled refresh to repository.** Checkout master → fetch provider rows → choose one endpoint per slug → fetch model scores → resolve and fetch LiveBench → exact joins → price filter → coverage checks → optional minimal projection → JSON write → commit and push. Source failures generally stop publication, but validation and file-write guarantees have gaps described below.
2.  **Browser comparison.** Fetch JSON → admit rows with a cost and any score → build selectors → derive time bounds → select metric and model groups → include unknown response times → apply provider-specific subscription factor → compute frontier → draw chart and table. The initial loader assumes more about numeric types and valid domains than the publisher guarantees.
3.  **Offline reproduction and failure.** All five local inputs avoid network access: two AA dumps, LiveBench CSV, categories, and metadata. A missing/failed mandatory LiveBench source aborts the whole refresh intentionally. Current tests cover those failures before opening the output, but not failures during output writing.
4.  **Benchmark identity.** AA model slugs are the join key. LiveBench mappings deliberately omit unverified Fable and GLM identities. Release, source commit, effort, revision, and partial-subtask counts survive minimal output. This restraint is appropriate and should remain.
5.  **Delivery to users.** Repository automation ends at git push. No tracked step establishes that the new JSON reached the public site. This is a separate boundary from a successful scrape.

### Positive findings and proportionality

-   Zero runtime package dependencies and plain static hosting keep installation and operational costs low.
-   LiveBench files use one resolved commit; input schema, duplicate conflicts, effort-specific joins, and partial results have useful checks.
-   SciCode and Terminal-Bench scores reject booleans and out-of-range values and preserve valid zero scores.
-   Dynamic model/provider/provenance strings pass through `esc` at HTML insertion points. Production code does not evaluate downloaded code. URLs are hardcoded HTTPS endpoints; there are no application secrets, user accounts, or server-side authorization paths to redesign.
-   Browser frontier computation is sorting plus a scan, O(n log n). With 141 loaded rows, there is no measured reason for workers, caching infrastructure, or a visualization framework.
-   Rendering and parser functions are already separable enough for targeted tests. A wholesale module split would add churn without fixing the high-impact defects.

## Prioritized findings

Priority reflects impact and likelihood, not file size. “Confirmed” means observed in code and, where stated, reproduced with controlled local inputs. It does not mean the current public site has experienced the failure. Effort estimates are engineering days for someone familiar with this repository, including tests and documentation.

| Rank | ID  | Finding | User or operational impact | Likelihood | Effort / change risk | Dependencies |
| --- | --- | --- | --- | --- | --- | --- |
| 1   | F1  | Invalid rows survive publication and break browser numeric assumptions | A single bad row can invalidate JSON or chart geometry | Medium under upstream drift; reproduced | 1–2 days / medium | Define field contract; precede deployment changes |
| 2   | F2  | Terminal-Bench guard checks source presence instead of usable joined coverage | A successful refresh can publish an empty supported benchmark | Medium; prior renamed-field incident makes this relevant | 0.5–1 day / low | Reuse F1 eligibility rules |
| 3   | F3  | Existing tests are absent from all automated gates | Changes can reach the daily publisher without regression checks | Certain configuration gap; failure frequency unknown | 0.5 day / low | Can be addressed first |
| 4   | F4  | Successful data commits are not connected to verified site publication or visible freshness | Readers may keep using stale prices and scores | Conditional deployment risk; freshness omission confirmed | 1–2 days / medium | Verify Pages settings first; deploy only validated artifacts |
| 5   | F5  | Output replacement is not atomic | Interrupted/manual refresh can destroy the last usable local JSON | Lower likelihood, confirmed failure mode | 0.5 day / low | Serialize validated F1 output |
| 6   | F6  | Empty/time-less data has no defined UI state; large filter layout threatens fullscreen | Stuck loading or unusable controls; possible clipped chart | Edge-state defects confirmed; layout risk unverified | 0.5–1.5 days / low–medium | F1, real-browser verification for layout |
| 7   | F7  | Current documentation contradicts parser behavior; subscription assumptions lack provenance | Misdiagnosis of upstream changes and overconfident cost comparisons | Documentation errors certain; estimate misuse uncertain | 0.5–1 day / low | Update alongside the relevant fixes |

### F1. Dataset-wide numeric validation is missing

**Confirmed defect.** `main` at `artificialanalysis.ai-parser.py:427` uses truthiness for token prices, while 435–459 only establish that at least one eligible row exists for required metrics. Other exported rows remain unchecked. `value_or_none` at 155 handles RSC placeholder strings but is not a numeric validator. `clean_model` at 304–341 directly propagates most numeric fields and performs arithmetic on others. `json.dump` at 475 permits nonstandard NaN/Infinity by default.

The browser loader at `intelligence-vs-cost.html:394–396` accepts any non-null cost. `render` at 626–641 uses every admitted cost to calculate logarithmic bounds; formatting at 367–369, 692, and 784 assumes actual numbers.

**Reproduction.** Using the existing parser test harness, one valid row plus a second row with cost 0, -1, "bad", or NaN all published successfully. The NaN case wrote a literal NaN token. Reusing the actual inline UI script with the existing DOM harness, a valid positive-cost row plus a zero-cost row generated SVG containing NaN.

**Impact.** Nonstandard JSON fails browser JSON parsing; zero/negative costs poison the logarithmic axis for the whole chart; strings can cause formatter errors. The present snapshot contains no invalid loaded costs, so this is an exposed failure path, not a claim of currently corrupt data.

**Related ambiguity.** Zero token prices are excluded as “missing” at line 427, while negative values are truthy. Decide token-price validity independently from positive task-cost eligibility. Missing scores and missing response times are valid states and must not be converted into measured zeroes.

### F2. Coverage guards do not guarantee usable benchmark output

**Confirmed defect.** `artificialanalysis.ai-parser.py:431–434` checks whether any extracted model has `terminalBench40`, before considering whether its slug joined a priced, nondeprecated, positive-cost output row. SciCode and LiveBench use stronger post-join checks at 435–459. There is no equivalent default Intelligence-view gate, and no loss-of-coverage diagnostic against a prior snapshot.

**Reproduction.** A valid exported row with SciCode and LiveBench, plus Terminal-Bench only on a different, unexported slug, exits successfully and writes `terminalbench_v4_0: null` for every output row. Existing tests at `tests/test_parser.py:115–135` test missing Terminal-Bench source data, but not this wrong-slug condition with otherwise valid scores.

**Impact.** A supported chart can become empty while the update job reports success. More broadly, a severely reduced provider feed can pass if the small required subset survives. Do not treat “one score exists somewhere” as completeness.

**Backlog relationship.** Task \[2\] fixed the actual field spelling and regenerated scores. This finding extends its failure-preservation boundary; it is not a request to repeat or reopen the completed rename fix.

### F3. No automated regression gate

**Confirmed architectural risk.** The only tracked workflow has schedule and workflow\_dispatch triggers at `.github/workflows/update-models.yml:3–6`. It runs the parser at 25–26 and commits at 28–39. It never invokes either test suite, has no pull-request test job, and does not check the resulting JSON with the browser's contract.

**Evidence.** All 15 Python test methods passed. The documented Node command passed; directly running `node tests/test_ui.cjs` also reported all six named tests passing. These tests are useful, but their success currently depends on a maintainer running them. Python tests focus on recent benchmark integrations. DOM stubs at `tests/test_ui.cjs:26–63` cannot validate CSS, native fullscreen, focus behavior, or real event propagation.

**Impact.** The daily writer can execute a regression after merge without any test gate. A read-only CI job using existing test tools is proportionate; a new framework is unnecessary.

### F4. Repository refresh, public delivery, and freshness are not one verified path

**Conditional deployment risk and confirmed observability gap.** The workflow ends with `git push origin HEAD:master` at `.github/workflows/update-models.yml:39`. Checkout does not specify alternative credentials. No deployment workflow is tracked. README links a Pages site at line 3 but does not explain its publishing source or refresh-to-deploy relationship.

GitHub documents that commits pushed with GITHUB\_TOKEN do not trigger a Pages build. If this repository uses branch-based Pages with the default checkout token, a daily data commit alone will not update the site. This is conditional because Pages settings and run history were not available in the checkout. [GitHub Pages publishing-source documentation](https://docs.github.com/en/pages/getting-started-with-github-pages/configuring-a-publishing-source-for-your-github-pages-site).

The public-page fetch through the web tool failed; that is not evidence that the site is down.

Freshness is also not visible in the UI. Only matched LiveBench rows carry `retrieved_at`, from `fetch_livebench` at parser line 71. AA responses have no recorded retrieval time or source fingerprint. `livebenchScore` at HTML 731–736 displays release, model, and subtask count, but no retrieval time. Footer 304–308 supplies no snapshot date. A LiveBench failure at parser 419–421 intentionally freezes the whole file, including unrelated AA prices.

**Impact.** A preserved last-good snapshot can remain plausible indefinitely. A recent LiveBench fetch time does not establish when its source results changed, nor the age of AA measurements.

**Secondary evidence.** A new LiveBench retrieval timestamp on every successful run means byte-level diff at workflow line 31 normally reports changes even when scores and upstream commit are identical. These are audit commits, not necessarily data changes. Keep that distinction explicit rather than silently discarding provenance.

### F5. “Leave output unchanged” does not cover write failures

**Confirmed defect.** `artificialanalysis.ai-parser.py:474–475` opens the destination with "w" and streams serialization directly into it.

**Reproduction.** Patching only `json.dump` to write a short prefix and raise OSError left the temporary output as `[partial`, replacing the test harness's previous dataset. Existing preservation tests fail before this write point and therefore pass.

**Impact and scope.** Manual or local scheduled runs can lose their last usable dataset on interruption or storage failure. The current GitHub job will not commit after a nonzero parser exit, so this does not prove master is corrupted by a failed job. Nonetheless, the CLI's persistence boundary should match its documented preservation behavior.

### F6. UI edge states are incomplete; fullscreen layout needs a real-browser check

**Confirmed edge defects.**

-   An empty loaded array reaches `render` at `intelligence-vs-cost.html:601`, which returns without replacing the initial loading message. A controlled empty-array run kept “Loading model data”.
-   When every admitted model lacks response time, `Math.min(...times)` and `Math.max(...times)` at 398–400 yield Infinity and -Infinity. A controlled one-row run reproduced those bounds. A single identical minimum/maximum time also leaves `secondsToSlider` at 480 with a zero denominator.
-   The broad fetch-chain catch at 408–412 calls rendering/type errors “Could not load models.json” and suggests starting a server even after a successful fetch.

**Layout risk, not browser-confirmed.** CSS at 109–113 combines a full-height, overflow-hidden card with nonshrinking filters. All 28 provider groups and 100 model controls render expanded at 430–438. Fullscreen chart geometry at 637–639 assumes at least 520 units even after subtracting controls. On short/narrow viewports the filters can consume the available height, leaving the chart or controls inaccessible. The Node stubs assign a constant 20-pixel offsetHeight and cannot establish actual behavior.

**Impact.** Edge datasets leave confusing controls or status. Large selectors may defeat the completed fullscreen feature. Verify layout before selecting the smallest fix.

### F7. Current reference documentation has drifted

**Confirmed discrepancies.**

-   `README.md:125–128` still names `terminalbenchV40`; parser 227 and historical task \[2\] identify `terminalBench40`. This is operationally important when repairing another upstream change.
-   README 18 and diagram 100 summarize first-party preference ahead of completeness. `deduplicate_models.sort_key` at parser 264–273 ranks pricing and plot completeness before first-party status.
-   README 94–102 omits the models-feed and LiveBench acquisition paths. Line 108 mentions bracket-counting although extraction uses a JSON decoder.
-   Parser header 3–10 calls the script `fetch_aa.py`; line 346 mentions a nonexistent `aiprice.html`.
-   README coverage values at 79–90 are undated older snapshot figures. HTML footer 307 says models without intelligence or speed are excluded; loader 394–396 and filter 610 intentionally allow other scored models and unknown response times.
-   README 201 says the time filter identifies models fast enough for the use case, without explaining that unknown-time models remain visible. This is intentional behavior covered by `tests/test_ui.cjs:102`, not a reason to silently change the filter.

**Architectural interpretation risk.** `PLANS` at HTML 333–340 hardcodes fees, estimated allowances, and separate multipliers, but only multipliers affect `effectiveCost` at 372. Help text at 227–232 and 258–262 labels the result an estimate, which is good. There is no source, effective date, or derivation for the assumed allowance values, and no proof every model from a provider is available under the chosen subscription. This review does not assert current commercial prices or quotas. Preserve API defaults; describe alternative plans as explicit comparison scenarios unless their assumptions can be substantiated.

## Ordered remediation plan

All steps below are recommendations for a future authorized implementation. No changes were made as part of this review.

### Step 1. Make existing checks automatic and capture the reproduced failures

Addresses F3 and establishes protection for F1, F2, F5, and F6. No prerequisite.

-   Add a read-only pull-request/push validation workflow with explicit supported Python and Node versions. Run the existing unittest and Node commands. Run the same tests before the scheduled workflow fetches or commits.
-   Add small offline regression cases for mixed valid/invalid rows, unmatched Terminal-Bench scores, interrupted output writes, empty UI data, and absent/equal response-time bounds. Add a compact AA stream fixture capturing the relevant real response shape when a source dump is available; do not check in multi-megabyte dumps just to test a few fields.
-   During implementation, land each new failing case with its corresponding fix; keep commits green. Maintain one documented test invocation in README and CI.

**Acceptance and verification.** Both suites execute on proposed code changes; a deliberately failing assertion blocks validation in a temporary branch/check. Pull-request checks need no write token or network data. Scheduled tests run before publication. Existing 15 Python methods and six Node tests remain green.

**Benefit.** Protects subsequent changes at low cost. **Migration/rollback.** No data migration. Revert workflow configuration independently if needed; do not grant write permissions to the test job. Confirm branch protection separately before claiming checks block merge.

### Step 2. Enforce one publication contract and atomically preserve the last good file

Addresses F1 and F5. Depends on Step 1 regression protection.

Affected modules: parser normalization, price selection, output serialization; UI loader; parser/UI tests; README schema and failure behavior.

-   Define the accepted types and units for every exported field. Use finite numeric checks that reject booleans. Keep missing measurements null; use nonnegative token prices where free pricing is valid, positive cost for logarithmic plotting, and explicit domain checks for each benchmark.
-   Validate all rows, not just a row that satisfies a coverage gate. Malformed upstream values must produce an actionable source/slug/field diagnostic and abort publication. If an invalid optional measurement is intentionally converted to null, document and test that policy explicitly.
-   Avoid silently coercing arbitrary strings. Preserve the JSON array shape, existing keys, metric URLs, and legitimate null/zero benchmark behavior.
-   Serialize with strict JSON, rejecting NaN/Infinity. Write to a temporary sibling of the destination, finish and close it, then replace the destination atomically; clean up the temporary file on errors.
-   At the browser boundary, admit only valid positive finite plot costs and finite selected scores, with an explicit invalid-data diagnostic. Do not let one invalid cost set global chart bounds.

**Acceptance and verification.** Mixed valid/bad fixtures cannot publish invalid JSON; zero/negative/string/boolean/nonfinite values are exercised by field domain. Existing valid output preserves its meanings. Simulated serialization/write/replacement failures preserve prior bytes. A successful refresh produces a complete file. UI tests generate no NaN/Infinity geometry from rejected inputs. Strictly parse the checked-in snapshot as a compatibility check.

**Benefit.** Prevents one bad row from breaking every chart and protects local last-good data. **Migration/rollback.** No schema migration. Compare output against the existing snapshot before rollout to detect unintended row losses. Roll back code and restore the prior Git snapshot if policy rejects legitimate source values; never relax validation silently in the publication path.

### Step 3. Gate benchmark coverage after the actual joins and eligibility rules

Addresses F2. Depends on Step 2's field and eligibility contract.

Affected modules: `extract_model_indexes`, `main` coverage validation, parser tests, README Terminal-Bench and refresh sections.

-   Apply post-join checks to default Intelligence and all explicitly required benchmark views, including Terminal-Bench. Do not require every benchmark on every row.
-   Calculate counts on the output population with the same nondeprecated/positive-cost eligibility policy used for publication and chart defaults.
-   Keep the deliberate strict LiveBench refresh policy for now. It already has tests and documentation; partial refreshes need a separate product decision and source-age semantics.
-   Report input rows, unique slugs, exported rows, source scores, matched scores, and eligible scores. Compare available prior-snapshot counts and warn clearly about large losses. If a blocking loss threshold is desired, calibrate and document it from actual refreshes rather than hardcoding today's 411 rows or six mappings.
-   Correct README's Terminal-Bench source key in the same change. Link the new regression to completed task \[2\]'s historical explanation without changing its status.

**Acceptance and verification.** Source-only Terminal-Bench on an unjoined slug fails and preserves output. Zero scores remain valid. Deprecated-only and zero-cost-only coverage fails. Legitimately missing scores on individual rows remain null. A valid complete fixture passes in full and minimal modes. Lost coverage diagnostics identify source failure versus join failure.

**Benefit.** Stops “green refresh, empty chart” regressions without adding more scraping infrastructure. **Migration/rollback.** No output schema change. Stricter failures retain the prior snapshot. Review rejected source fixtures before changing the gate; do not publish an empty view to make the job green.

### Step 4. Establish and document the refresh-to-site path, with source freshness

Addresses F4. Read-only deployment verification can start immediately; publication changes depend on Steps 1–3.

Affected areas: update workflow, any future Pages deployment workflow, parser snapshot metadata, UI footer/status, README operations instructions.

-   First inspect repository Pages settings and recent runs. Determine the configured source, authentication used for data commits, last deployed commit, and whether a scheduled refresh actually produced a deployment. Compare deployed HTML/JSON with a known repository snapshot. This decides whether the conditional deployment finding applies.
-   If daily commits do not reach the site, use an explicit Pages artifact/deployment job after successful validation, or an equally documented supported publishing path. Package the exact validated HTML and JSON together. Do not assume a GITHUB\_TOKEN push triggers another workflow.
-   Record AA retrieval time/source fingerprints and LiveBench source commit/retrieval time. Distinguish last successful acquisition from the benchmark release and any available upstream measurement date.
-   Preserve the existing JSON-array consumer contract. Prefer a small companion metadata file tied to the JSON by a content hash over changing the root shape without migration. Publish the pair in one site artifact; the UI must tolerate absent metadata and label a hash mismatch as unknown freshness.
-   Display snapshot age and source identity in the page. Document that a mandatory source failure preserves and ages the whole snapshot. Add an operator runbook for failed refreshes, source drift, non-fast-forward push rejection, manual refresh, and restoring a prior snapshot.
-   Keep direct pushes non-forcing. If master advanced during a scrape, fail/retry from current master rather than overwriting unrelated commits. Decide explicitly whether retrieval-only changes deserve daily audit commits; do not confuse them with score changes.

**Acceptance and verification.** A later authorized test deployment proves that a validated refresh appears at the public URL and matches the intended dataset hash. Failed tests/acquisition/validation publish nothing. The UI distinguishes missing/old metadata from a fresh snapshot. Older JSON without metadata still loads. A rollback exercise identifies the previous HTML/JSON/metadata artifact and its provenance.

**Benefit.** Makes the operational result observable to maintainers and readers. **Migration/rollback.** Pages source changes require recording prior settings and retaining the previous artifact. Introduce metadata compatibly before requiring it. Actual deployment remains outside this review's authorization.

### Step 5. Define UI edge states and verify the expanded-selector layout

Addresses F6. Depends on Step 2 loader behavior; can proceed independently of Pages work.

Affected modules: HTML fetch/initialization, render status, time-slider helpers, fullscreen/filter CSS; UI tests; README behavior descriptions.

-   Render an explicit empty-dataset state. Separate network/JSON errors from invalid-data or rendering failures so users receive the right recovery instruction.
-   For no known response times, disable or neutralize the time control with an explanation. For equal bounds, use a defined conversion instead of dividing by zero. Preserve the existing policy that unknown response times remain visible, and state it beside the control/help.
-   Test the current 28-provider/100-checkbox layout in a real browser at desktop, mobile, and short fullscreen sizes, including fallback fullscreen. Check chart visibility, all filter controls, exit, keyboard focus, and table access.
-   If clipping is confirmed, use the smallest correction, such as collapsible provider groups and an independently scrollable filter region, while reserving usable chart space. Do not redesign the whole page preemptively.
-   Keep the existing lightweight Node tests. Add only a small browser smoke test if automated browser execution is adopted; a documented repeatable manual check is acceptable at this scale.

**Acceptance and verification.** Empty, single-row, all-null-time, and equal-time fixtures have truthful status and finite control bounds. Existing filter/URL tests pass. All controls and the chart remain reachable at the tested viewport sizes, using mouse and keyboard. Unknown-time behavior is explicit.

**Benefit.** Removes confusing states and protects completed selector/fullscreen functionality. **Migration/rollback.** No data migration. Preserve URL parameter names and selection semantics; CSS changes can roll back independently.

### Step 6. Finish the reference documentation and make cost scenarios auditable

Addresses F7 and lower-priority semantic inconsistencies. Depends on the final behavior from earlier steps; code-adjacent corrections should already have landed with their fixes.

Affected documents: README, parser module docstring and minimal-output docstring, HTML help/footer; PLANS and its tests if scenario handling changes.

-   Describe the two AA feeds plus LiveBench, exact deduplication order, source identities, output contract, offline inputs, mandatory-source failure policy, tests, schedule, deployment, and recovery.
-   Replace undated coverage claims with a clearly dated example or a reproducible count command. Do not hand-maintain parallel “current” counts.
-   Correct stale filenames, bracket-counting wording, Terminal-Bench spelling, and statements that intelligence/speed are mandatory for every view.
-   For subscription scenarios, document the assumed fee/allowance derivation and date where evidence exists. Otherwise label values as illustrative assumptions. Display the applied factor; derive it from one set of assumptions instead of maintaining duplicate fee/allowance/multiplier facts if those values remain.
-   Preserve API pricing as default. Explain that AA Intelligence Index task cost is a proxy when plotting other benchmarks and that subscription availability is not established merely by provider identity.
-   Keep task \[2\]'s failure report and task \[3\]'s worktree path as explicitly historical provenance. Do not rewrite historical research as current implementation requirements.

**Acceptance and verification.** Every documented CLI example references an existing file and can run with local fixtures. Documentation matches tested filtering and deduplication. Scenario tests confirm affected providers and API-default identity behavior. A reader can distinguish measured costs, estimated scenarios, unknown response times, and missing scores.

**Benefit.** Makes maintenance and interpretation less error-prone. **Migration/rollback.** No schema changes. If scenario assumptions cannot be substantiated, retain API comparisons and clearly label or remove only the unsupported scenario choices in a separately reviewed change.

The sequence puts cheap automated checks first, then protects dataset correctness and persistence before making publication more reliable. It prevents shipping bad data faster. UI behavior and documentation follow the stabilized contract. Deployment verification itself can happen early because it is read-only.

## Existing backlog and research reconciliation

TASKS.md has empty Ordered backlog, Scheduled, and In Progress sections. All numbered items \[1\]–\[3\] are Completed. No current backlog item already owns this hardening plan.

-   **\[1\] Provider/model selectors:** implementation is present in HTML 419–469. F6 is a follow-up integration risk with fullscreen, not missing selector work.
-   **\[2\] Terminal-Bench field parsing:** `docs/tasks/2-terminal-bench-field-parsing.md:3–5` explicitly marks the report historical and identifies the fix/data commits. Current code uses the corrected field and the snapshot has 151 scores. F2 adds missing join-level protection; F7 fixes README drift.
-   **\[3\] Additional benchmarks:** `docs/tasks/3-additional-coding-benchmarks.md:7–10` records LiveBench completion and explicitly says other research candidates were not all implemented. The six reviewed mappings and null unmatched identities match that scope.
-   **Completed inline items:** daily refresh, Y zoom, touchpad scrolling, fullscreen, SciCode restoration, and Terminal-Bench selection are represented in code. Their presence is not proof every edge case is correct.
-   **Research recommendations:** `docs/coding-benchmark-research.md:85–89` proposes additional data sources. These are research candidates, not missing completed features. Do not schedule more integrations before the current publication contract is dependable.
-   The latest history includes tracker maintenance at `4309168`, `74b5829`, `f60e579`, and `ec29a22`. Their clarifications were respected. No task documents, bullets, statuses, references, or Kandev child tasks were changed or created.

## Lower-priority findings and watch points

-   **Pareto ties:** HTML 575–583 returns only the first model at identical cost and score. A two-identical-row probe returned A only. Under conventional dominance semantics both are nondominated; current snapshot frontiers had no exact ties. When fixing, separate frontier coordinates from membership, add equal-cost/equal-score tests, and align the “both smarter and cheaper” prose at 291–293 with the chosen definition.
-   **RSC drift and conflicts:** parser 185 selects the first exact rows marker; 215 requires an exact compact models marker; 226–232 merges duplicate score objects with last valid score winning. Add a bounded fixture for unexpected whitespace/duplicate conflicting scores when next touching extraction. No evidence justifies a full RSC protocol decoder.
-   **Missing values:** parser 335–336 turns zero timing into null by truthiness; tooltip HTML 755 renders null speed as 0 through Math.round. Preserve the distinction when applying F1's field contract.
-   **Transport resilience:** requests have timeouts but no bounded retries or explicit response-size cap. Consider a small retry policy for transient errors only if run history shows failures; never retry deterministic schema errors or add a queue for this daily job.
-   **Supply chain and privileges:** the workflow grants contents:write and references checkout by major tag. Keep tests read-only; evaluate immutable action references and deployment-scoped permissions when editing CI. No exploit was demonstrated.
-   **Single-file organization:** retain the Python script and standalone page unless repeated cross-cutting changes make extraction useful. The missing numeric contract and test gate matter more than moving existing functions into more files.
-   **Research currency:** external source coverage and commercial plan assumptions were not re-researched. Historical “researched September 18” claims are preserved as historical evidence, not asserted as current facts.

## Verification record and limitations

Completed non-destructive checks:

-   Clean initial and final git status; HEAD recorded above.
-   Full tracked-file inventory and recent source/data/tracker history inspection.
-   `PYTHONDONTWRITEBYTECODE=1 python3 -m unittest discover -s tests -v`: 15 methods passed.
-   `node --test tests/test_ui.cjs`: passed; `node tests/test_ui.cjs`: six named cases passed. Environment Node v24.19.0.
-   Whole-snapshot JSON parsing, field coverage, duplicate-slug detection, eligible-population checks, invalid-cost checks, selector counts, and frontier-tie checks.
-   Temporary/mocked reproductions for mixed invalid costs, unmatched Terminal-Bench coverage, interrupted writes, zero-cost SVG geometry, empty dataset state, unknown time bounds, and tied frontier membership.
-   Current session/profile/workflow verified read-only through Kandev.
-   Official GitHub Pages documentation checked for token-trigger behavior; public site fetch was unsuccessful through the web tool.

No production refresh, paid calls, code changes, commits, deployment, new task, or tracker maintenance occurred. AA raw dumps are not checked in, so current upstream RSC shape and identity mappings were not independently revalidated against live responses. No real-browser executable or PinchTab CLI was found in the checked command paths, so responsive layout/fullscreen concerns remain hypotheses pending the specified browser checks. Actual GitHub Pages settings, branch protection, and workflow/deployment history were not inspected. These limits do not affect the local reproductions of F1, F2, F5, and the F6 data-state defects.

Completion criterion met: the architecture review, evidence, priority order, and concrete remediation steps are ready for user review. Implementation requires a separate instruction.
