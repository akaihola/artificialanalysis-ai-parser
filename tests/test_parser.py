import contextlib
import copy
import importlib.util
import io
import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

SPEC = importlib.util.spec_from_file_location(
    "parser", Path(__file__).resolve().parents[1] / "artificialanalysis.ai-parser.py"
)
parser = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(parser)

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
            {"slug": "test", "terminalbenchV40": 0.25},
            {"slug": "other", "terminalbenchV40": 0.9},
        ])
        for later in [{}, {"terminalbenchV40": None}, {"terminalbenchV40": True}]:
            raw += b"\n" + stream("models", [{"slug": "test", **later}])
        model = parser.clean_model(ROW, parser.extract_model_indexes(raw))
        self.assertEqual(model["terminalbench_v4_0"], 25)
        self.assertEqual(model["intelligence_index"], 42)
        self.assertEqual(model["math_index"], 75)
        for scores in [{}, {"terminalbenchHard": 0.9, "terminalbenchV21": 0.8},
                       {"slug": "test-other", "terminalbenchV40": 0.5}]:
            raw = stream("models", [{"slug": "test", **scores}])
            self.assertIsNone(parser.clean_model(ROW, parser.extract_model_indexes(raw))["terminalbench_v4_0"])

    def test_score_validation(self):
        for source, target in [("scicode", "coding_index"),
                               ("terminalbenchV40", "terminalbench_v4_0")]:
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

    def run_main(self, directory, rows, scores, minimal=False):
        output = Path(directory) / "output.json"
        output.write_bytes(b"previous dataset\n")
        args = ["parser", "--out", str(output)] + (["--minimal"] if minimal else [])
        with patch("sys.argv", args), patch.object(
            parser, "fetch_rsc", side_effect=[rows, scores]
        ), contextlib.redirect_stdout(io.StringIO()):
            parser.main()
        return json.loads(output.read_text())

    def test_success(self):
        for minimal in [False, True]:
            with self.subTest(minimal=minimal), tempfile.TemporaryDirectory() as directory:
                data = self.run_main(directory, stream("rows", [ROW]),
                                     stream("models", [{"slug": "test", "scicode": 0}]), minimal)
                self.assertEqual(data[0]["coding_index"], 0)
                self.assertIsNone(data[0]["terminalbench_v4_0"])
                self.assertEqual("agentic_index" in data[0], not minimal)

    def test_terminalbench_output(self):
        for minimal in [False, True]:
            for score in [0, 0.25]:
                with self.subTest(minimal=minimal, score=score), tempfile.TemporaryDirectory() as directory:
                    data = self.run_main(directory, stream("rows", [ROW]), stream("models", [
                        {"slug": "test", "scicode": 0.5, "terminalbenchV40": score},
                    ]), minimal)
                    self.assertEqual(data[0]["terminalbench_v4_0"], score * 100)
                    self.assertEqual(data[0]["coding_index"], 50)

    def test_failed_refresh_preserves_output(self):
        valid = stream("models", [{"slug": "test", "scicode": 0.5}])
        cases = [(None, valid), (stream("rows", [ROW]), None),
                 (stream("rows", [ROW]), stream("models", [{"slug": "test"}])),
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


if __name__ == "__main__":
    unittest.main()
