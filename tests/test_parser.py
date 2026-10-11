import contextlib
import copy
import importlib.util
import io
import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch
from urllib.error import URLError

SPEC = importlib.util.spec_from_file_location(
    "parser", Path(__file__).resolve().parents[1] / "artificialanalysis.ai-parser.py"
)
parser = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(parser)

FIXTURES = Path(__file__).parent / "fixtures"
LIVEBENCH_INPUT = (
    (FIXTURES / "livebench.csv").read_bytes(),
    json.loads((FIXTURES / "livebench-categories.json").read_text()),
    json.loads((FIXTURES / "livebench-metadata.json").read_text()),
)

ROW = {
    "label": "Test model",
    "model": {"slug": "test", "intelligenceIndex": 42, "aime25": 0.75},
    "pricing": {
        "price1mInputTokens": 1, "price1mOutputTokens": 2, "costPerTask": 0.5,
    },
}


def stream(key, values):
    return ('1:' + json.dumps({key: values}, separators=(",", ":"))).encode()


# The models leaderboard repeats the site navigation: releases (families) and
# a models array that links each variant slug to its release.
def nav(slug="test"):
    return stream("modelsAndReleases", {
        "releases": [{"slug": "test-family", "name": "Test Family", "deprecated": False,
                      "releaseDate": "2026-09-22",
                      "creator": {"slug": "test-lab", "name": "Test Lab", "logo": "/img/logos/t.svg"}}],
        "models": [{"slug": slug, "name": "Test model (Xhigh, Default Fallback)",
                    "releaseSlug": "test-family"}],
    })


def scores(slug="test", **fields):
    """Models leaderboard stream for one slug with a model-level cost."""
    return nav(slug) + b"\n" + stream("models", [
        {"slug": slug, "intelligenceIndexCostPerTask": 0.25, **fields}])


class ParserTests(unittest.TestCase):
    def test_scicode_join_and_scaling(self):
        raw = stream("models", [{"slug": "test"}, {"slug": "other"}])
        raw += b"\n" + stream("models", [
            {"slug": "test", "scicode": 0.25, "codingIndex": 99, "agenticIndex": 8},
            {"slug": "other", "scicode": 0.9},
        ])
        # Later metadata must not erase a score from an earlier array.
        raw += b"\n" + stream("models", [{"slug": "test"}])
        model = parser.clean_model(ROW, parser.extract_model_indexes(raw))
        self.assertEqual(model["coding_index"], 25)
        self.assertEqual(model["agentic_index"], 8)
        self.assertEqual(model["intelligence_index"], 42)
        self.assertEqual(model["math_index"], 75)

    def test_terminalbench_join_and_version(self):
        raw = stream("models", [
            {"slug": "test", "terminalBench40": 0.25},
            {"slug": "other", "terminalBench40": 0.9},
        ])
        for later in [{}, {"terminalBench40": None}, {"terminalBench40": True}]:
            raw += b"\n" + stream("models", [{"slug": "test", **later}])
        model = parser.clean_model(ROW, parser.extract_model_indexes(raw))
        self.assertEqual(model["terminalbench_v4_0"], 25)
        self.assertEqual(model["intelligence_index"], 42)
        self.assertEqual(model["math_index"], 75)
        for scores in [{}, {"terminalbenchHard": 0.9, "terminalbenchV21": 0.8},
                       {"slug": "test-other", "terminalBench40": 0.5}]:
            raw = stream("models", [{"slug": "test", **scores}])
            self.assertIsNone(parser.clean_model(ROW, parser.extract_model_indexes(raw))["terminalbench_v4_0"])

    def test_score_validation(self):
        for source, target in [("scicode", "coding_index"),
                               ("terminalBench40", "terminalbench_v4_0")]:
            for value in [None, "$undefined", "0.5", True, False, -0.1, 1.1,
                          float("nan"), float("inf"), -float("inf"), 0, 1, 0.0, 1.0, 0.25]:
                with self.subTest(source=source, value=value):
                    raw = stream("models", [{"slug": "test", source: value}])
                    model = parser.clean_model(ROW, parser.extract_model_indexes(raw))
                    expected = value * 100 if type(value) in (int, float) and 0 <= value <= 1 else None
                    self.assertEqual(model[target], expected)
        for scores in [{}, {"codingIndex": 99}, {"slug": "test-other", "scicode": 0.5}]:
            raw = stream("models", [{"slug": "test", **scores}])
            self.assertIsNone(parser.clean_model(ROW, parser.extract_model_indexes(raw))["coding_index"])

    def run_main(self, directory, rows, scores, minimal=False, livebench=LIVEBENCH_INPUT):
        output = Path(directory) / "output.json"
        output.write_bytes(b"previous dataset\n")
        args = ["parser", "--out", str(output)] + (["--minimal"] if minimal else [])
        with patch("sys.argv", args), patch.object(
            parser, "fetch_rsc", side_effect=[rows, scores]
        ), patch.object(parser, "fetch_livebench", return_value=livebench,
                        side_effect=livebench if isinstance(livebench, Exception) else None), patch.dict(
            parser.LIVEBENCH_MODELS, {"gpt-6-astra-max": ("test", "max", None)}
        ), contextlib.redirect_stdout(io.StringIO()):
            parser.main()
        return json.loads(output.read_text())

    def test_success(self):
        for minimal in [False, True]:
            with self.subTest(minimal=minimal), tempfile.TemporaryDirectory() as directory:
                data = self.run_main(directory, stream("rows", [ROW]),
                                     scores(scicode=0, terminalBench40=0), minimal)
                self.assertEqual(data[0]["coding_index"], 0)
                self.assertEqual(data[0]["terminalbench_v4_0"], 0)
                self.assertEqual("agentic_index" in data[0], not minimal)
                self.assertEqual({k: data[0][k] for k in [
                    "family", "family_name", "lab", "lab_name", "released", "effort",
                    "effort_order", "cost_per_task",
                ]}, {
                    "family": "test-family", "family_name": "Test Family", "lab": "test-lab",
                    "lab_name": "Test Lab", "released": "2026-09-22", "effort": "xhigh",
                    "effort_order": 50, "cost_per_task": 0.25,
                })

    def test_terminalbench_output(self):
        for minimal in [False, True]:
            for score in [0, 0.25]:
                with self.subTest(minimal=minimal, score=score), tempfile.TemporaryDirectory() as directory:
                    data = self.run_main(directory, stream("rows", [ROW]),
                                         scores(scicode=0.5, terminalBench40=score), minimal)
                    self.assertEqual(data[0]["terminalbench_v4_0"], score * 100)
                    self.assertEqual(data[0]["coding_index"], 50)

    def test_failed_refresh_preserves_output(self):
        valid = scores(scicode=0.5, terminalBench40=0.5)
        rows = stream("rows", [ROW])
        cases = [(None, valid), (rows, None), (rows, scores()),
                 (rows, scores(scicode=0.5, terminalbenchV40=0.5)),
                 (rows, nav() + b"\n" + stream("models", [{"slug": "other", "scicode": 0.5}])),
                 # Without the navigation block there are no families.
                 (rows, stream("models", [{"slug": "test", "scicode": 0.5, "terminalBench40": 0.5,
                                           "intelligenceIndexCostPerTask": 0.5}]))]
        for section, field, values in [
            ("pricing", "price1mInputTokens", [None, 0]),
            ("model", "deprecated", [True]),
        ]:
            for value in values:
                row = copy.deepcopy(ROW)
                row[section][field] = value
                cases.append((stream("rows", [row]), valid))
        # The host row's costPerTask (0.5 in ROW) must not stand in for the model-level cost.
        for value in [None, "$undefined", 0, -1, True, "bad", float("inf"), float("nan")]:
            cases.append((rows, scores(scicode=0.5, terminalBench40=0.5,
                                       intelligenceIndexCostPerTask=value)))
        for i, (rows_raw, models_raw) in enumerate(cases):
            with self.subTest(case=i), tempfile.TemporaryDirectory() as directory:
                with self.assertRaises(SystemExit) as error:
                    self.run_main(directory, rows_raw, models_raw)
                self.assertEqual(error.exception.code, 1)
                self.assertEqual((Path(directory) / "output.json").read_bytes(), b"previous dataset\n")

    def test_parse_effort(self):
        for name, reasoning, expected in [
            ("Claude Opus 5.5 (Xhigh, Default Fallback)", True, ("xhigh", 50)),
            ("Claude Opus 5.5 (xhigh with fallback)", True, ("xhigh", 50)),
            ("Claude Fable 5 (Max, Opus 4.8 Fallback)", True, ("max", 60)),
            ("Claude Fable 5 (with fallback)", True, ("max", 60)),
            ("GPT-6.1 Sol (High)", True, ("high", 40)),
            ("GPT-6 Astra (medium)", True, ("medium", 30)),
            ("GPT-6 Luna (low)", True, ("low", 20)),
            ("GPT-5 (Minimal)", False, ("minimal", 10)),
            ("GPT-6 Sol (Daybreak Blue, max)", True, ("max", 60)),
            ("GLM-5.3 Turbo (max, Based on GLM-5.2)", True, ("max", 60)),
            ("Gemini 4 Argon (high) AI Studio (1M output)", True, ("high", 40)),
            ("DeepSeek V4 Pro (Non-reasoning)", False, ("none", 0)),
            ("Claude Opus 4.7 (Non-reasoning, High)", False, ("none", 0)),
            ("Claude Opus 4.7 (Non-reasoning, High)", True, ("none", 0)),
            ("Solar Pro 2 (Reasoning)", True, ("default", 35)),
            ("Mercury 2", True, ("default", 35)),
            ("Llama 4 Maverick", False, ("none", 0)),
            ("Gemini 2.5 Flash (Sep '25)", False, ("none", 0)),
            # Qwen's "Max" is part of the model name, not an effort.
            ("Qwen3.8 Max (0902)", True, ("default", 35)),
            ("Qwen3.7 Max", False, ("none", 0)),
            ("Qwen3 Max Thinking (Preview)", True, ("default", 35)),
            (None, True, ("default", 35)),
            (None, False, ("none", 0)),
        ]:
            with self.subTest(name=name, reasoning=reasoning):
                self.assertEqual(parser.parse_effort(name, reasoning), expected)

    def test_model_level_metadata_and_performance(self):
        row = copy.deepcopy(ROW)
        row["label"] = "Test model (high)"  # host label; AA's model name wins
        row["model"]["reasoningModel"] = True
        row["host"] = {"name": "Some Host"}
        row["performance"] = {"medianEndToEndResponseTimeSeconds": 10,
                              "medianOutputTokensPerSecond": 5,
                              "medianTimeToFirstTokenSeconds": 1}
        raw = scores(intelligenceIndexCostPerTask=3.25,
                     medianEndToEndResponseTimeSeconds=133.998,
                     medianOutputTokensPerSecond=80.5,
                     medianTimeToFirstTokenSeconds=2.5)
        # Later metadata must not erase values from an earlier array.
        raw += b"\n" + stream("models", [{"slug": "test", "name": None, "releaseSlug": "$undefined",
                                         "intelligenceIndexCostPerTask": None,
                                         "medianEndToEndResponseTimeSeconds": None}])
        model = parser.clean_model(row, parser.extract_model_indexes(raw))
        self.assertEqual({k: model[k] for k in [
            "family", "family_name", "lab", "lab_name", "released", "effort", "effort_order",
            "cost_per_task", "e2e_response_time_s", "output_tokens_per_second",
            "time_to_first_token_ms", "provider", "price_1m_input_tokens", "name",
        ]}, {
            "family": "test-family", "family_name": "Test Family", "lab": "test-lab",
            "lab_name": "Test Lab", "released": "2026-09-22", "effort": "xhigh", "effort_order": 50,
            "cost_per_task": 3.25, "e2e_response_time_s": 134.0, "output_tokens_per_second": 80.5,
            "time_to_first_token_ms": 2500.0, "provider": "Some Host", "price_1m_input_tokens": 1,
            "name": "Test model (high)",
        })
        # No model-level data: no host-level stand-ins; effort comes from the host label.
        model = parser.clean_model(row, {})
        for key in ["family", "family_name", "lab", "lab_name", "released", "cost_per_task",
                    "e2e_response_time_s", "output_tokens_per_second", "time_to_first_token_ms"]:
            self.assertIsNone(model[key], key)
        self.assertEqual((model["effort"], model["effort_order"]), ("high", 40))
        for bad in [None, "$undefined", -1, True, "1", float("inf"), float("nan")]:
            with self.subTest(bad=bad):
                raw = scores(intelligenceIndexCostPerTask=bad, medianEndToEndResponseTimeSeconds=bad,
                             medianOutputTokensPerSecond=bad, medianTimeToFirstTokenSeconds=bad)
                model = parser.clean_model(row, parser.extract_model_indexes(raw))
                for key in ["cost_per_task", "e2e_response_time_s", "output_tokens_per_second",
                            "time_to_first_token_ms"]:
                    self.assertIsNone(model[key], key)

    def test_release_metadata_validation(self):
        nav = {"releases": [{"slug": "fam", "name": "$undefined", "releaseDate": "Sep 2026",
                             "creator": "$c:props:creator"}],
               "models": [{"slug": "a", "name": "A (low)", "releaseSlug": "fam"},
                          {"slug": "b", "name": "A (high)", "releaseSlug": "fam"},
                          {"slug": "c", "name": "C", "releaseSlug": "unknown"}]}
        indexes = parser.extract_model_indexes(stream("modelsAndReleases", nav))
        a, b, c = (parser.clean_model({"model": {"slug": s}}, indexes) for s in "abc")
        self.assertEqual((a["family"], b["family"]), ("fam", "fam"))
        self.assertEqual((a["effort"], b["effort"]), ("low", "high"))
        for key in ["family_name", "lab", "lab_name", "released"]:
            self.assertIsNone(a[key], key)
        # A release missing from the navigation leaves the family unknown.
        self.assertIsNone(c["family"])

    def test_livebench_fixture_and_compatibility(self):
        indexes = parser.parse_livebench(*LIVEBENCH_INPUT)
        self.assertEqual(set(indexes), {v[0] for v in parser.LIVEBENCH_MODELS.values()})
        self.assertNotIn("claude-fable-5-1", indexes)
        self.assertNotIn("glm-5-3", indexes)
        row = copy.deepcopy(ROW)
        row["model"]["slug"] = "gpt-6-astra"
        aa = {"gpt-6-astra": {"scicode": 0.7, "terminalBench40": 0.5}}
        before = parser.clean_model(row, aa)
        after = parser.clean_model(row, aa, indexes)
        self.assertAlmostEqual(after["livebench_coding"], (80.435 + 80.282) / 2)
        self.assertAlmostEqual(after["livebench_agentic_coding"], (63.636 + 43.333 + 65) / 3)
        for key in before:
            if not key.startswith("livebench"):
                self.assertEqual(before[key], after[key], key)
        for slug in ["gpt-6-astra-high", "gpt-6-astra-medium", "gpt-6-astra-2027", "unknown"]:
            row["model"]["slug"] = slug
            self.assertIsNone(parser.clean_model(row, aa, indexes)["livebench_coding"])

    def test_livebench_cells_and_duplicates(self):
        header = b"model,code_generation,code_completion,javascript,typescript,python\n"
        for cells, expected in [("0,0,0,0,0", (0, 0, 2, 3)),
                                ("100,N/A,0,-,60", (100, 30, 1, 2)),
                                (",N/A,-,,", (None, None, 0, 0))]:
            with self.subTest(cells=cells):
                raw = header + ("gpt-6-astra-max," + cells + "\n").encode()
                result = parser.parse_livebench(raw, *LIVEBENCH_INPUT[1:])["gpt-6-astra"]
                self.assertEqual(result["livebench_coding"], expected[0])
                self.assertEqual(result["livebench_agentic_coding"], expected[1])
                counts = result["livebench"]["subtasks"]
                self.assertEqual(counts["livebench_coding"], {"completed": expected[2], "expected": 2})
                self.assertEqual(counts["livebench_agentic_coding"], {"completed": expected[3], "expected": 3})
        valid_row = b"gpt-6-astra-max,0,0,0,0,0\n"
        self.assertEqual(len(parser.parse_livebench(header + valid_row * 2, *LIVEBENCH_INPUT[1:])), 1)
        invalid = [header + valid_row + b"gpt-6-astra-max,1,0,0,0,0\n",
                   b"model,code_generation\ngpt-6-astra-max,1\n",
                   header + b"gpt-6-astra-max,0,0,0\n",
                   header + b"gpt-6-astra-max,0,0,0,0,0,extra\n"]
        for value in ["nan", "inf", "-inf", "101", "-1"]:
            invalid.append(header + f"gpt-6-astra-max,{value},0,0,0,0\n".encode())
        for raw in invalid:
            with self.subTest(raw=raw), self.assertRaises(ValueError):
                parser.parse_livebench(raw, *LIVEBENCH_INPUT[1:])
        with patch.dict(parser.LIVEBENCH_MODELS, {"gpt-5.6-sol-max": ("gpt-6-astra", "max", None)}), self.assertRaisesRegex(ValueError, "conflicting LiveBench mappings"):
            parser.parse_livebench(*LIVEBENCH_INPUT)

    def test_livebench_unknown_source_effort_and_revision(self):
        header = b"model,code_generation,code_completion,javascript,typescript,python\n"
        for source_id in ["gpt-6-astra-high", "gpt-6-astra-2027-max", "deepseek-v4-flash-0731"]:
            with self.subTest(source_id=source_id):
                raw = header + f"{source_id},1,2,3,4,5\n".encode()
                self.assertEqual(parser.parse_livebench(raw, *LIVEBENCH_INPUT[1:]), {})

    def test_livebench_zero_scores_survive_refresh(self):
        raw = b"model,code_generation,code_completion,javascript,typescript,python\ngpt-6-astra-max,0,0,0,0,0\n"
        with tempfile.TemporaryDirectory() as directory:
            data = self.run_main(directory, stream("rows", [ROW]), scores(scicode=0, terminalBench40=0),
                                 livebench=(raw, *LIVEBENCH_INPUT[1:]))
            self.assertEqual(data[0]["livebench_coding"], 0)
            self.assertEqual(data[0]["livebench_agentic_coding"], 0)

    def test_livebench_metadata_and_schema(self):
        for key, value in [("release", "old"), ("commit", "main"),
                           ("retrieved_at", "not a date"), ("retrieved_at", "2026-09-18")]:
            provenance = {**LIVEBENCH_INPUT[2], key: value}
            with self.subTest(key=key), self.assertRaises(ValueError):
                parser.parse_livebench(*LIVEBENCH_INPUT[:2], provenance)
        with self.assertRaises(ValueError):
            parser.parse_livebench(LIVEBENCH_INPUT[0], {"Coding": []}, LIVEBENCH_INPUT[2])

    def test_livebench_full_minimal_and_no_response_time(self):
        for minimal in [False, True]:
            with self.subTest(minimal=minimal), tempfile.TemporaryDirectory() as directory:
                data = self.run_main(directory, stream("rows", [ROW]),
                                     scores(scicode=0.5, terminalBench40=0.5), minimal)
                self.assertIsNone(data[0]["e2e_response_time_s"])
                self.assertGreater(data[0]["livebench_coding"], 0)
                meta = data[0]["livebench"]
                self.assertEqual(meta["source_model"], "gpt-6-astra-max")
                self.assertEqual(meta["commit"], LIVEBENCH_INPUT[2]["commit"])
                self.assertEqual(meta["reasoning_effort"], "max")
                self.assertIsNone(meta["agent"])
                self.assertIsNone(meta["model_revision"])

    def test_livebench_failed_refresh_preserves_output(self):
        header = b"model,code_generation,code_completion,javascript,typescript,python\n"
        cases = [b"wrong header", header + b"unknown,1,2,3,4,5\n",
                 header + b"gpt-6-astra-max,,,1,2,3\n",
                 header + b"gpt-6-astra-max,1,2,,,\n"]
        valid = scores(scicode=0.5, terminalBench40=0.5)
        for raw in cases:
            with self.subTest(raw=raw), tempfile.TemporaryDirectory() as directory:
                with self.assertRaises(SystemExit):
                    self.run_main(directory, stream("rows", [ROW]), valid,
                                  livebench=(raw, *LIVEBENCH_INPUT[1:]))
                self.assertEqual((Path(directory) / "output.json").read_bytes(), b"previous dataset\n")
        with tempfile.TemporaryDirectory() as directory:
            with self.assertRaises(SystemExit):
                self.run_main(directory, stream("rows", [ROW]), valid, livebench=URLError("offline"))
            self.assertEqual((Path(directory) / "output.json").read_bytes(), b"previous dataset\n")

    def test_livebench_fetch_uses_one_commit(self):
        commit = LIVEBENCH_INPUT[2]["commit"]
        responses = [json.dumps({"sha": commit}).encode(), LIVEBENCH_INPUT[0],
                     json.dumps(LIVEBENCH_INPUT[1]).encode()]
        with patch.object(parser, "urlopen", side_effect=[io.BytesIO(r) for r in responses]) as download:
            raw, categories, provenance = parser.fetch_livebench()
        self.assertEqual(raw, LIVEBENCH_INPUT[0])
        self.assertEqual(categories, LIVEBENCH_INPUT[1])
        self.assertEqual(provenance["commit"], commit)
        for call in download.call_args_list[1:]:
            self.assertIn("/" + commit + "/public/", call.args[0].full_url)
            self.assertNotIn("rsc", call.args[0].headers)
        with patch.object(parser, "urlopen", return_value=io.BytesIO(b'{"sha":"main"}')), self.assertRaises(ValueError):
            parser.fetch_livebench()

    def test_livebench_offline_cli(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            row = copy.deepcopy(ROW)
            row["model"]["slug"] = "gpt-6-astra"
            (root / "aa.txt").write_bytes(stream("rows", [row]))
            (root / "scores.txt").write_bytes(scores("gpt-6-astra", scicode=0.5, terminalBench40=0.5))
            args = ["parser", "--file", str(root / "aa.txt"), "--models-file", str(root / "scores.txt"),
                    "--livebench-file", str(FIXTURES / "livebench.csv"),
                    "--livebench-categories-file", str(FIXTURES / "livebench-categories.json"),
                    "--livebench-metadata-file", str(FIXTURES / "livebench-metadata.json"),
                    "--out", str(root / "out.json"), "--minimal"]
            with patch("sys.argv", args), patch.object(parser, "urlopen", side_effect=AssertionError("network")), contextlib.redirect_stdout(io.StringIO()):
                parser.main()
            self.assertEqual(json.loads((root / "out.json").read_text())[0]["livebench"]["source_model"], "gpt-6-astra-max")


if __name__ == "__main__":
    unittest.main()
