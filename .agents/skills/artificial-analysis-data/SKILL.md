---
name: artificial-analysis-data
description: Maintain this repository's Artificial Analysis and LiveBench feed acquisition, diagnose daily refresh failures, or replay downloaded leaderboard data.
---

# Leaderboard data acquisition

Verified 2026-11-11 against live responses and the sites' shipped JavaScript.
Use the implementation in [the parser](../../../artificialanalysis.ai-parser.py)
and the captured [schema fixture](../../../tests/fixtures/aa-leaderboards-2026-11-11.json)
to reproduce these formats. Recheck live responses when a refresh fails.

- Artificial Analysis still serves RSC at `/leaderboards/providers?_rsc=hgvan`
  and `/leaderboards/models?_rsc=hgvan` with the parser's `RSC_HEADERS`.
  `initialRows` and `initialModels` contain only current models: 527 provider rows
  and 285 models on the verification date. Each page's `manifest` supplies a
  public `/data/<hash>.txt` path and hex key for the complete dataset: 1,169
  provider rows and 734 models, including deprecated models.
- Match the website's payload decoder: hex-decode the key, derive the 12-byte
  nonce from `SHA256(key)[:12]`, authenticate/decrypt AES-GCM with a 128-bit tag
  and no associated data, decompress gzip, then parse the JSON array. Use
  `cryptography`, installed from the repository's pinned requirements. The key
  is public page data and requires no user credential.
- Benchmark fractions moved under `scores`: `scicode`, `terminalbench-4-0`
  and `aime-2025`. Model-level `outputSpeed` and `timeToFirstToken` replace the
  former median-prefixed fields. `intelligenceIndexCostPerTask` remains present.
  End-to-end response time is absent. Keep it unknown: the new
  `intelligenceIndexTimePerTask` measures a different workload.
- `fetch_rsc()` appends the decoded complete array to the returned bytes.
  Save that result for replay with `--file` and `--models-file`. A saved raw
  page alone contains only the current-model subset. Manifest failures must
  abort a refresh rather than fall back to that subset.
- LiveBench's former `LiveBench/new-livebench` repository and raw URLs return
  404. The official site serves the original benchmark at
  `https://livebench.ai/v1/table_2026_06_25.csv` and
  `https://livebench.ai/v1/categories_2026_06_25.json`; these retain the six
  reviewed model IDs. The public `LiveBench/livebench.github.io` main branch
  has an older CSV missing those IDs. Keep the original release and reviewed
  mappings when restoring acquisition; LiveBench 2.0 is a different benchmark.
- Archive provenance records source URLs, retrieval time, CSV SHA-256 and the
  SHA-256 of category JSON serialized with sorted keys and compact separators.
  It has `commit: null`; historical commit-based offline metadata still works.
  File hashes identify downloaded content, not an atomic upstream revision.

The regression suite exercises these formats and verifies that a failed full
download leaves the previous output intact:

```bash
python3 -m unittest tests.test_parser -v
```

Use [check-live-data.sh](scripts/check-live-data.sh) for the existing Chromium
and Firefox smoke tests against the repository's current dataset. On atom,
verified 2026-11-11, `UV_CONSTRAINT` pins Playwright 1.64 to the installed Nix
browser builds. Greenlet also needs GCC's `libstdc++.so.6` on `LD_LIBRARY_PATH`.
The helper handles these and checks the Playwright import explicitly: otherwise
the browser suite reports skipped tests when a native library is missing.

For a refresh-fix PR in this repository, verified 2026-11-11: the GitHub connector
returned HTTP 403 `Resource not accessible by integration` on PR creation, while
the existing authenticated `gh pr create --body-file` succeeded. That failure is
specific to the connector's permissions, not the local GitHub CLI credentials.
