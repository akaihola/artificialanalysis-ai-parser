# Restore the daily model refresh

Antti and chart readers no longer receive refreshed model data because the daily
GitHub Actions parser step fails with `rows not found in response`.

Owner: Codex in this thread. Next action: reproduce the provider-feed failure,
update acquisition and parsing for the verified upstream schema, add regression
coverage, and run a full refresh without replacing the last good data on failure.

Failure: [daily refresh job](https://github.com/akaihola/artificialanalysis-ai-parser/actions/runs/42805407520/job/129793147490), 2026-11-10.

Acceptance: the same refresh command succeeds with live data, parser tests pass,
and existing benchmark meanings and output-preservation checks remain intact.
