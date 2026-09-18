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
                                     stream("models", [{"slug": "test", "scicode": 0, "terminalBench40": 0}]), minimal)
                self.assertEqual(data[0]["coding_index"], 0)
                self.assertEqual(data[0]["terminalbench_v4_0"], 0)
                self.assertEqual("agentic_index" in data[0], not minimal)

    def test_terminalbench_output(self):
        for minimal in [False, True]:
            for score in [0, 0.25]:
                with self.subTest(minimal=minimal, score=score), tempfile.TemporaryDirectory() as directory:
                    data = self.run_main(directory, stream("rows", [ROW]), stream("models", [
                        {"slug": "test", "scicode": 0.5, "terminalBench40": score},
                    ]), minimal)
                    self.assertEqual(data[0]["terminalbench_v4_0"], score * 100)
                    self.assertEqual(data[0]["coding_index"], 50)

    def test_failed_refresh_preserves_output(self):
        valid = stream("models", [{"slug": "test", "scicode": 0.5, "terminalBench40": 0.5}])
        cases = [(None, valid), (stream("rows", [ROW]), None),
                 (stream("rows", [ROW]), stream("models", [{"slug": "test"}])),
                 (stream("rows", [ROW]), stream("models", [{"slug": "test", "scicode": 0.5, "terminalbenchV40": 0.5}])),
                 (stream("rows", [ROW]), stream("models", [{"slug": "other", "scicode": 0.5}]))]
        for section, field, values in [
            ("pricing", "price1mInputTokens", [None, 0]),
            ("model", "deprecated", [True]),
            ("pricing", "costPerTask", [None, 0, -1, True, "bad", float("inf"), float("nan")]),
        ]:
            for value in values:
                row = copy.deepcopy(ROW)
                row[section][field] = value
                cases.append((stream("rows", [row]), valid))
        for i, (rows, scores) in enumerate(cases):
            with self.subTest(case=i), tempfile.TemporaryDirectory() as directory:
                with self.assertRaises(SystemExit) as error:
                    self.run_main(directory, rows, scores)
                self.assertEqual(error.exception.code, 1)
                self.assertEqual((Path(directory) / "output.json").read_bytes(), b"previous dataset\n")


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
            data = self.run_main(directory, stream("rows", [ROW]), stream("models", [
                {"slug": "test", "scicode": 0, "terminalBench40": 0},
            ]), livebench=(raw, *LIVEBENCH_INPUT[1:]))
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
                data = self.run_main(directory, stream("rows", [ROW]), stream("models", [
                    {"slug": "test", "scicode": 0.5, "terminalBench40": 0.5},
                ]), minimal)
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
        scores = stream("models", [{"slug": "test", "scicode": 0.5, "terminalBench40": 0.5}])
        for raw in cases:
            with self.subTest(raw=raw), tempfile.TemporaryDirectory() as directory:
                with self.assertRaises(SystemExit):
                    self.run_main(directory, stream("rows", [ROW]), scores,
                                  livebench=(raw, *LIVEBENCH_INPUT[1:]))
                self.assertEqual((Path(directory) / "output.json").read_bytes(), b"previous dataset\n")
        with tempfile.TemporaryDirectory() as directory:
            with self.assertRaises(SystemExit):
                self.run_main(directory, stream("rows", [ROW]), scores, livebench=URLError("offline"))
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
            (root / "scores.txt").write_bytes(stream("models", [
                {"slug": "gpt-6-astra", "scicode": 0.5, "terminalBench40": 0.5},
            ]))
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
