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

import argparse
import csv
import io
import json
import math
import os
import re
import sys
from datetime import datetime, timezone
from urllib.error import URLError
from urllib.request import Request, urlopen

RSC_URL = "https://artificialanalysis.ai/leaderboards/providers?_rsc=hgvan"
MODELS_RSC_URL = "https://artificialanalysis.ai/leaderboards/models?_rsc=hgvan"
RSC_HEADERS = {
    "accept": "*/*",
    "rsc": "1",
    "next-router-prefetch": "1",
    "next-router-state-tree": '[["","pages",["leaderboards",["models",["__PAGE__",{},"/leaderboards/models","refresh"]]]],null,null,true]',
    "next-url": "/leaderboards/models",
    "user-agent": "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/138.0.0.0 Safari/537.36",
}

LIVEBENCH_RELEASE = "2026_06_25"
LIVEBENCH_ROOT = "https://raw.githubusercontent.com/LiveBench/new-livebench"
LIVEBENCH_CATEGORIES = {
    "livebench_coding": ("Coding", ["code_generation", "code_completion"]),
    "livebench_agentic_coding": ("Agentic Coding", ["javascript", "typescript", "python"]),
}
# Reviewed against LiveBench modelLinks.js and AA's exact effort-specific slugs.
# Fable's fallback variants and GLM's unspecified effort are intentionally absent.
LIVEBENCH_MODELS = {
    "gpt-6-astra-max": ("gpt-6-astra", "max", None),
    "gpt-5.6-sol-max": ("gpt-5-6-sol", "max", None),
    "gpt-5.6-terra-max": ("gpt-5-6-terra", "max", None),
    "gpt-5.6-luna-max": ("gpt-5-6-luna", "max", None),
    "gemini-3.8-flash-high": ("gemini-3-8-flash", "high", None),
    "deepseek-v4.1-flash-max": ("deepseek-v4-1-flash", "max", "2026-09-10"),
}


def fetch_livebench():
    """Fetch both release files from one commit, without AA's RSC headers."""
    def download(url):
        request = Request(url, headers={"User-Agent": "artificialanalysis-ai-parser"})
        with urlopen(request, timeout=60) as response:
            return response.read()

    commit = json.loads(download(
        "https://api.github.com/repos/LiveBench/new-livebench/commits/main"
    ))["sha"]
    if not isinstance(commit, str) or not re.fullmatch(r"[0-9a-f]{40}", commit):
        raise ValueError("invalid LiveBench commit")
    base = f"{LIVEBENCH_ROOT}/{commit}/public"
    raw = download(f"{base}/table_{LIVEBENCH_RELEASE}.csv")
    categories = json.loads(download(f"{base}/categories_{LIVEBENCH_RELEASE}.json"))
    return raw, categories, {
        "release": LIVEBENCH_RELEASE, "commit": commit,
        "retrieved_at": datetime.now(timezone.utc).isoformat(),
    }


def parse_livebench(raw, categories, provenance):
    """Join only reviewed identities; retain partial evaluation provenance."""
    if not isinstance(provenance, dict) or provenance.get("release") != LIVEBENCH_RELEASE:
        raise ValueError("unexpected LiveBench release")
    commit = provenance.get("commit")
    if not isinstance(commit, str) or not re.fullmatch(r"[0-9a-f]{40}", commit):
        raise ValueError("invalid LiveBench commit")
    retrieved_at = provenance.get("retrieved_at")
    if not isinstance(retrieved_at, str) or datetime.fromisoformat(retrieved_at).tzinfo is None:
        raise ValueError("LiveBench retrieval time must include a timezone")
    for category, columns in LIVEBENCH_CATEGORIES.values():
        if not isinstance(categories, dict) or categories.get(category) != columns:
            raise ValueError(f"unexpected LiveBench category: {category}")
    reader = csv.DictReader(io.StringIO(raw.decode("utf-8-sig")), strict=True)
    required = {"model"} | {c for _, cols in LIVEBENCH_CATEGORIES.values() for c in cols}
    headers = reader.fieldnames or []
    if not required.issubset(headers) or len(headers) != len(set(headers)):
        raise ValueError("missing or duplicate LiveBench columns")
    indexes, seen, unmatched = {}, {}, []
    for row in reader:
        source_id = row["model"]
        if not source_id or None in row or any(row[c] is None for c in required):
            raise ValueError("malformed LiveBench row")
        if source_id in seen:
            if row != seen[source_id]:
                raise ValueError(f"conflicting LiveBench rows: {source_id}")
            continue
        seen[source_id] = row
        scores, counts = {}, {}
        for metric, (_, columns) in LIVEBENCH_CATEGORIES.items():
            values = []
            for column in columns:
                try:
                    score = float(row[column])
                except ValueError:
                    continue  # Empty and nonnumeric cells are missing evaluations.
                if not math.isfinite(score) or not 0 <= score <= 100:
                    raise ValueError(f"invalid LiveBench score: {source_id}/{column}")
                values.append(score)
            scores[metric] = sum(values) / len(values) if values else None
            counts[metric] = {"completed": len(values), "expected": len(columns)}
        if source_id not in LIVEBENCH_MODELS:
            unmatched.append(source_id)
            continue
        slug, effort, revision = LIVEBENCH_MODELS[source_id]
        if slug in indexes:
            raise ValueError(f"conflicting LiveBench mappings: {slug}")
        indexes[slug] = {
            **scores,
            "livebench": {
                "source_model": source_id, "release": LIVEBENCH_RELEASE,
                "source_url": f"{LIVEBENCH_ROOT}/{commit}/public/table_{LIVEBENCH_RELEASE}.csv",
                "commit": commit, "retrieved_at": retrieved_at,
                "reasoning_effort": effort, "model_revision": revision,
                "agent": None, "subtasks": counts,
            },
        }
    print(f"LiveBench: {len(indexes)} mapped rows; {len(unmatched)} unreviewed IDs")
    if unmatched:
        print("Unmatched LiveBench IDs: " + ", ".join(unmatched))
    return indexes


def fetch_rsc(url=RSC_URL, timeout=60):
    """Download an RSC stream from artificialanalysis.ai."""
    print(f"Downloading RSC data from {url} ...")
    req = Request(url, headers=RSC_HEADERS)
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


def extract_model_indexes(raw):
    """Extract SciCode, Terminal-Bench v4.0 and Agentic scores by model slug.

    SciCode replaces the Coding Index missing from the current feed.
    This function finds all "models" JSON arrays in the stream and maps
    model slugs to numeric scores.
    """
    text = raw.decode("utf-8", errors="replace")
    indexes = {}
    decoder = json.JSONDecoder()
    pos = 0
    while True:
        idx = text.find('"models":[', pos)
        if idx < 0:
            break
        pos = idx + 10
        try:
            models, _ = decoder.raw_decode(text, text.find('[', idx))
        except json.JSONDecodeError:
            continue
        for m in models:
            if not isinstance(m, dict) or not m.get("slug"):
                continue
            entry = indexes.setdefault(m["slug"], {})
            for key in ("scicode", "terminalBench40"):
                score = m.get(key)
                if type(score) in (int, float) and 0 <= score <= 1:
                    entry[key] = score
            if isinstance(m.get("agenticIndex"), (int, float)):
                entry["agenticIndex"] = m["agenticIndex"]
    return indexes


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


def clean_model(entry, indexes=None, livebench=None):
    """Extract clean model data from a raw entry.

    `indexes` maps a model slug to scores from the models leaderboard
    (see extract_model_indexes). coding_index holds SciCode scaled to
    0-100, replacing the composite Coding Index missing from the feed.
    terminalbench_v4_0 holds Terminal-Bench v4.0 scaled to 0-100.

    The site does not publish a Math Index anymore. As a stand-in,
    math_index holds the AIME 2025 math contest score (0-100). It is
    None for models that Artificial Analysis did not test on AIME.
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
    model_indexes = (indexes or {}).get(model.get("slug"), {})
    scicode = model_indexes.get("scicode")
    terminalbench = model_indexes.get("terminalBench40")
    aime25 = value_or_none(model.get("aime25"))
    livebench_scores = (livebench or {}).get(model.get("slug"), {})

    return {
        "name": entry.get("label", "?"),
        "creator": creator.get("name", host.get("name", "?")),
        "provider": host.get("name", "?"),
        "slug": model.get("slug", ""),
        "intelligence_index": value_or_none(model.get("intelligenceIndex")),
        "coding_index": scicode * 100 if scicode is not None else None,
        "terminalbench_v4_0": terminalbench * 100 if terminalbench is not None else None,
        "livebench_coding": livebench_scores.get("livebench_coding"),
        "livebench_agentic_coding": livebench_scores.get("livebench_agentic_coding"),
        "livebench": livebench_scores.get("livebench"),
        "math_index": aime25 * 100 if aime25 is not None else None,
        "agentic_index": model_indexes.get("agenticIndex"),
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
        "intelligence_index", "coding_index", "math_index", "terminalbench_v4_0",
        "cost_per_task",
        "price_1m_input_tokens", "price_1m_output_tokens", "price_1m_cache_hit",
        "blended_price_3_1", "context_window_tokens",
        "output_tokens_per_second", "time_to_first_token_ms", "e2e_response_time_s",
        "reasoning", "open_weights", "deprecated",
        "livebench_coding", "livebench_agentic_coding", "livebench",
    ]
    return [{k: m[k] for k in keep} for m in models]


def main():
    parser = argparse.ArgumentParser(description="Fetch AI model data from artificialanalysis.ai")
    parser.add_argument("--file", help="Parse existing RSC dump file (skip download)")
    parser.add_argument("--models-file", help="Parse existing models leaderboard dump file (skip download)")
    parser.add_argument("--livebench-file", help="Local LiveBench score CSV (requires both companion files)")
    parser.add_argument("--livebench-categories-file", help="Local LiveBench category JSON")
    parser.add_argument("--livebench-metadata-file", help="Local JSON with release, commit, retrieved_at")
    parser.add_argument("--out", default="models.json", help="Output JSON file (default: models.json)")
    parser.add_argument("--minimal", action="store_true", help="Output only calculator-essential fields")
    parser.add_argument("--pretty", action="store_true", help="Pretty-print JSON output")
    args = parser.parse_args()
    local_livebench = [args.livebench_file, args.livebench_categories_file, args.livebench_metadata_file]
    if any(local_livebench) and not all(local_livebench):
        parser.error("all three LiveBench file inputs are required for local LiveBench data")

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

    # Step 4: Get benchmark scores from the models leaderboard.
    if args.models_file:
        with open(args.models_file, "rb") as f:
            models_raw = f.read()
        print(f"Read {len(models_raw):,} bytes from {args.models_file}")
    else:
        models_raw = fetch_rsc(MODELS_RSC_URL)
    indexes = extract_model_indexes(models_raw) if models_raw else {}
    print(f"SciCode scores for {sum('scicode' in m for m in indexes.values())} models from the models leaderboard")

    try:
        if args.livebench_file:
            with open(args.livebench_file, "rb") as f:
                livebench_raw = f.read()
            with open(args.livebench_categories_file, encoding="utf-8") as f:
                categories = json.load(f)
            with open(args.livebench_metadata_file, encoding="utf-8") as f:
                provenance = json.load(f)
            livebench = parse_livebench(livebench_raw, categories, provenance)
        else:
            livebench = parse_livebench(*fetch_livebench())
    except (OSError, ValueError, KeyError, TypeError, csv.Error) as e:
        print(f"Error: LiveBench refresh failed: {e}. Output left unchanged.")
        sys.exit(1)

    # Step 5: Clean
    models = [clean_model(e, indexes, livebench) for e in deduped]

    # Remove entries without pricing
    models_with_price = [m for m in models if m["price_1m_input_tokens"] and m["price_1m_output_tokens"]]
    print(f"Models with pricing: {len(models_with_price)}")

    # Preserve the last usable dataset when the score feed or slug join breaks.
    if not any("terminalBench40" in m for m in indexes.values()):
        print("Error: no Terminal-Bench v4.0 scores; check the models leaderboard "
              "download and terminalBench40 field. Output left unchanged.")
        sys.exit(1)
    if not any(
        not m["deprecated"] and m["coding_index"] is not None
        and type(m["cost_per_task"]) in (int, float)
        and math.isfinite(m["cost_per_task"]) and m["cost_per_task"] > 0
        for m in models_with_price
    ):
        print("Error: no chart-eligible SciCode scores; check the models leaderboard "
              "download, scicode field, and slug joins. Output left unchanged.")
        sys.exit(1)

    for metric in LIVEBENCH_CATEGORIES:
        coverage = {}
        for m in models_with_price:
            if m[metric] is None:
                continue
            counts = coverage.setdefault(m["provider"], [0, 0])
            counts[0] += 1
            if (not m["deprecated"] and math.isfinite(m[metric])
                    and type(m["cost_per_task"]) in (int, float)
                    and math.isfinite(m["cost_per_task"]) and m["cost_per_task"] > 0):
                counts[1] += 1
        print(f"{metric} matched/eligible by provider: {coverage}")
        if not any(eligible for _, eligible in coverage.values()):
            print(f"Error: no chart-eligible {metric} scores. Output left unchanged.")
            sys.exit(1)
    missing_slugs = livebench.keys() - {m["slug"] for m in models_with_price}
    if missing_slugs:
        print("LiveBench mapped slugs absent from priced AA models: " + ", ".join(sorted(missing_slugs)))

    # Sort by intelligence index descending
    models_with_price.sort(key=lambda m: m["intelligence_index"] or 0, reverse=True)

    # Step 6: Output
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
