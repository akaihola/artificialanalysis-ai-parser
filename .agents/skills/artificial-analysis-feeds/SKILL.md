---
name: artificial-analysis-feeds
description: Diagnose or update this repository's Artificial Analysis leaderboard downloads and model identity joins.
---

# Artificial Analysis feeds

Verified 2026-11-14 against the public site and a live parser refresh:

- `/leaderboards/providers` and `/leaderboards/models` expose RSC data with
  current-only preview arrays and a `manifest` for the complete array.
  The public `/data/<hash>.txt` payload uses AES-GCM, with a hex key published
  in the page and the first 12 bytes of SHA-256(key) as its nonce. Decompress
  the decrypted gzip before decoding JSON. Use the parser's tested
  `fetch_manifest`; do not hard-code the changing paths or keys.
- These leaderboards no longer include model variant slugs. The public
  [model index](https://artificialanalysis.ai/models) has two manifests:
  endpoint measurements and an object containing a complete `models` array.
  Select that object by its shape. It supplies canonical IDs, slugs, names,
  short names and release slugs, including deprecated variants.
- Join model scores to that catalog by model ID. Provider row IDs identify
  endpoints, not models. For providers, match the longest complete canonical
  name or short name within the exact release, ignoring case and preserving
  the reasoning effort. Host labels can append a precision, speed or region.
  Missing or ambiguous matches must stop the refresh, preserving its output.
- A release slug identifies a family, not a variant: GPT-6 Astra max and xhigh
  share a release but have separate canonical slugs and benchmark results.
- The live check covered 741 catalog models and 1,165 provider rows. Name
  matches agreed with all 999 endpoint-to-model IDs in the comparison payload;
  the other 166 endpoints had no performance data. This is dated evidence,
  not a guarantee about later schemas.

Run `uv run --with-requirements requirements.txt python -m unittest tests.test_parser -v`.
Use `--out` with a temporary destination for live parser checks. The
[November 14 fixture](../../../tests/fixtures/aa-leaderboards-2026-11-14.json?f)
covers distinct efforts and deprecated models; tests also preserve the old output
when identity matching fails. Normalized downloads remain replayable through
the parser's existing offline inputs. Reusing a catalog is limited to one process.
