#!/usr/bin/env bash
set -euo pipefail

aa_repo_root="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")/../../../.." && pwd)"
cd "$aa_repo_root"
aa_playwright='playwright~=1.64.0'
if [[ -n "${UV_CONSTRAINT:-}" ]]; then
    aa_playwright="$(rg '^playwright[=<>~!]' "$UV_CONSTRAINT")"
fi
if [[ -n "${PLAYWRIGHT_BROWSERS_PATH:-}" ]] && command -v nix >/dev/null; then
    aa_gcc_lib="$(nix eval --raw --impure --expr '(import <nixpkgs> {}).stdenv.cc.cc.lib.outPath')"
    export LD_LIBRARY_PATH="${aa_gcc_lib}/lib${LD_LIBRARY_PATH:+:$LD_LIBRARY_PATH}"
fi
if [[ "$#" -eq 0 ]]; then
    set -- tests.test_ui.ChromiumTests.test_real_models_json_smoke \
        tests.test_ui.FirefoxTests.test_real_models_json_smoke
fi
uv run --with-requirements requirements.txt --with "$aa_playwright" \
    python -c 'from playwright.sync_api import sync_playwright'
uv run --with-requirements requirements.txt --with "$aa_playwright" \
    python -m unittest "$@" -v
