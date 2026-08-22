#!/usr/bin/env python3
"""
fetch_aa.py — Extract model data from artificialanalysis.ai RSC endpoint
No API key required. Outputs clean JSON for the cost calculator.

Usage:
    python3 fetch_aa.py                    # fetch + parse, save to models.json
    python3 fetch_aa.py --file aa.txt      # parse existing RSC dump
    python3 fetch_aa.py --out models.json  # custom output path
    python3 fetch_aa.py --minimal          # only fields needed for calculator
"""

import json
import sys
import os
import argparse
import time
from urllib.request import Request, urlopen
from urllib.error import URLError

RSC_URL = "https://artificialanalysis.ai/leaderboards/providers?_rsc=hgvan"
RSC_HEADERS = {
    "accept": "*/*",
    "rsc": "1",
    "next-router-prefetch": "1",
    "next-router-state-tree": '[["","pages",["leaderboards",["models",["__PAGE__",{},"/leaderboards/models","refresh"]]]],null,null,true]',
    "next-url": "/leaderboards/models",
    "user-agent": "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/138.0.0.0 Safari/537.36",
}


def fetch_rsc(timeout=60):
    """Download the RSC stream from artificialanalysis.ai."""
    print(f"Downloading RSC data from {RSC_URL} ...")
    req = Request(RSC_URL, headers=RSC_HEADERS)
    try:
        with urlopen(req, timeout=timeout) as resp:
            if resp.status != 200:
                print(f"Error: HTTP {resp.status}")
                return None
            raw = resp.read()
            print(f"Downloaded {len(raw):,} bytes")
            return raw
    except URLError as e:
        print(f"Network error: {e}")
        return None


def value_or_none(v):
    """Return None for RSC placeholder strings such as "$undefined".

    The RSC stream marks missing values with strings like "$undefined".
    This helper turns them into None. Real values pass through unchanged.
    """
    if isinstance(v, str) and v.startswith("$"):
        return None
    return v


def dict_or_empty(v):
    """Return v if it is a dict. Return an empty dict if it is not.

    Some entries hold a reference string (for example "$c:props:...")
    instead of a real object. This helper makes access safe.
    """
    return v if isinstance(v, dict) else {}


def extract_rows(raw):
    """Extract the leaderboard "rows" JSON array from the RSC stream.

    The RSC stream is text. It contains a large React tree. The tree has
    a "rows" key. Its value is a JSON array with one entry per host-model
    pair. We decode the JSON directly from that position. The JSON decoder
    finds the end of the array by itself, so brackets inside strings are
    not a problem.
    """
    text = raw.decode("utf-8", errors="replace")
    idx = text.find('"rows":')
    if idx < 0:
        print("Error: 'rows' not found in response")
        return None

    arr_start = text.find('[', idx)
    if arr_start < 0 or arr_start - idx > 50:
        print("Error: could not find array start after 'rows'")
        return None

    try:
        rows, _ = json.JSONDecoder().raw_decode(text, arr_start)
        return rows
    except json.JSONDecodeError as e:
        print(f"JSON parse error at position {e.pos}: {e.msg}")
        return None


def deduplicate_models(entries):
    """Keep one entry per model.

    Many hosts serve the same model. Price and speed differ per host.
    We pick one entry per model slug with these rules, in this order:

    1. Prefer an entry that has prices.
    2. Prefer an entry that also has cost per task, intelligence index,
       and end-to-end response time. The plot needs these three values.
    3. Prefer the entry from the model creator's own API.
    4. Prefer the entry with the lowest cost per task.

    We also give each kept entry the shortest label from its group.
    Host-specific labels are longer (for example "Gemini 3.5 Flash
    AI Studio"), so the shortest label is the clean model name.
    """
    groups = {}
    for entry in entries:
        slug = dict_or_empty(entry.get("model")).get("slug")
        if slug:
            groups.setdefault(slug, []).append(entry)

    def sort_key(entry):
        model = dict_or_empty(entry.get("model"))
        pricing = dict_or_empty(entry.get("pricing"))
        perf = dict_or_empty(entry.get("performance"))
        host = dict_or_empty(entry.get("host"))
        creator = dict_or_empty(model.get("creator"))
        cost_per_task = value_or_none(pricing.get("costPerTask"))
        has_prices = (value_or_none(pricing.get("price1mInputTokens")) is not None
                      and value_or_none(pricing.get("price1mOutputTokens")) is not None)
        complete = (cost_per_task is not None
                    and value_or_none(model.get("intelligenceIndex")) is not None
                    and value_or_none(perf.get("medianEndToEndResponseTimeSeconds")) is not None)
        first_party = host.get("name") == creator.get("name")
        # min() picks the best entry, so "good" must sort as "small".
        return (not has_prices, not complete, not first_party,
                cost_per_task if cost_per_task is not None else float("inf"))

    result = []
    for group in groups.values():
        best = min(group, key=sort_key)
        labels = [e.get("label") for e in group if e.get("label")]
        if labels:
            best["label"] = min(labels, key=len)
        result.append(best)
    return result


def clean_model(entry):
    """Extract clean model data from a raw entry.

    The site does not publish coding_index and math_index anymore.
    We keep the keys so older dashboards do not break. Their value
    is now always None.
    """
    model = dict_or_empty(entry.get("model"))
    perf = dict_or_empty(entry.get("performance"))
    pricing = dict_or_empty(entry.get("pricing"))
    features = dict_or_empty(entry.get("features"))
    host = dict_or_empty(entry.get("host"))
    creator = dict_or_empty(model.get("creator"))

    in_price = value_or_none(pricing.get("price1mInputTokens"))
    out_price = value_or_none(pricing.get("price1mOutputTokens"))
    blended = (3 * in_price + out_price) / 4 if in_price is not None and out_price is not None else None
    ttft_s = value_or_none(perf.get("medianTimeToFirstTokenSeconds"))
    e2e_s = value_or_none(perf.get("medianEndToEndResponseTimeSeconds"))

    return {
        "name": entry.get("label", "?"),
        "creator": creator.get("name", host.get("name", "?")),
        "provider": host.get("name", "?"),
        "slug": model.get("slug", ""),
        "intelligence_index": value_or_none(model.get("intelligenceIndex")),
        "coding_index": None,
        "math_index": None,
        "agentic_index": None,
        "cost_per_task": value_or_none(pricing.get("costPerTask")),
        "price_1m_input_tokens": in_price,
        "price_1m_output_tokens": out_price,
        "price_1m_cache_hit": value_or_none(pricing.get("cacheHitPrice")),
        "blended_price_3_1": blended,
        "context_window_tokens": value_or_none(features.get("contextWindowTokens")),
        "output_tokens_per_second": value_or_none(perf.get("medianOutputTokensPerSecond")),
        "time_to_first_token_ms": round(ttft_s * 1000, 1) if ttft_s else None,
        "e2e_response_time_s": round(e2e_s, 2) if e2e_s else None,
        "reasoning": model.get("reasoningModel", False),
        "open_weights": model.get("isOpenWeights", False),
        "deprecated": model.get("deprecated", False),
        "gpqa": value_or_none(model.get("gpqa")),
        "hle": value_or_none(model.get("hle")),
    }


def compress_for_calculator(models):
    """Return minimal fields needed by the aiprice.html calculator."""
    keep = [
        "name", "creator", "provider", "slug",
        "intelligence_index", "coding_index", "math_index",
        "cost_per_task",
        "price_1m_input_tokens", "price_1m_output_tokens", "price_1m_cache_hit",
        "blended_price_3_1", "context_window_tokens",
        "output_tokens_per_second", "time_to_first_token_ms", "e2e_response_time_s",
        "reasoning", "open_weights", "deprecated",
    ]
    return [{k: m[k] for k in keep} for m in models]


def main():
    parser = argparse.ArgumentParser(description="Fetch AI model data from artificialanalysis.ai")
    parser.add_argument("--file", help="Parse existing RSC dump file (skip download)")
    parser.add_argument("--out", default="models.json", help="Output JSON file (default: models.json)")
    parser.add_argument("--minimal", action="store_true", help="Output only calculator-essential fields")
    parser.add_argument("--pretty", action="store_true", help="Pretty-print JSON output")
    args = parser.parse_args()

    # Step 1: Get raw data
    if args.file:
        if not os.path.exists(args.file):
            print(f"Error: file '{args.file}' not found")
            sys.exit(1)
        with open(args.file, "rb") as f:
            raw = f.read()
        print(f"Read {len(raw):,} bytes from {args.file}")
    else:
        raw = fetch_rsc()
        if raw is None:
            sys.exit(1)

    # Step 2: Extract the leaderboard rows
    entries = extract_rows(raw)
    if entries is None:
        sys.exit(1)
    print(f"Extracted {len(entries)} raw entries (host-model pairs)")

    # Step 3: Deduplicate
    deduped = deduplicate_models(entries)
    print(f"Deduplicated to {len(deduped)} unique models")

    # Step 4: Clean
    models = [clean_model(e) for e in deduped]

    # Remove entries without pricing
    models_with_price = [m for m in models if m["price_1m_input_tokens"] and m["price_1m_output_tokens"]]
    print(f"Models with pricing: {len(models_with_price)}")

    # Sort by intelligence index descending
    models_with_price.sort(key=lambda m: m["intelligence_index"] or 0, reverse=True)

    # Step 5: Output
    if args.minimal:
        output = compress_for_calculator(models_with_price)
    else:
        output = models_with_price

    indent = 2 if args.pretty else None
    with open(args.out, "w", encoding="utf-8") as f:
        json.dump(output, f, indent=indent, ensure_ascii=False)

    size = os.path.getsize(args.out)
    print(f"\nSaved {len(output)} models to {args.out} ({size:,} bytes)")

    # Stats
    if output:
        top = output[0]
        print(f"\nTop model: {top['name']} ({top['creator']})")
        print(f"  IQ: {top['intelligence_index']} | Coding: {top['coding_index']} | Math: {top['math_index']}")
        print(f"  Price: ${top['price_1m_input_tokens']:.2f} in / ${top['price_1m_output_tokens']:.2f} out")
        if top.get("output_tokens_per_second"):
            print(f"  Speed: {top['output_tokens_per_second']:.0f} tok/s")


if __name__ == "__main__":
    main()
