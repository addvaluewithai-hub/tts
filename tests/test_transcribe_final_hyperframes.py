import importlib.util
import sys
import unittest
from pathlib import Path

MODULE_PATH = Path(__file__).resolve().parents[1] / "scripts" / "transcribe_final_hyperframes.py"
spec = importlib.util.spec_from_file_location("transcribe_final_hyperframes", MODULE_PATH)
module = importlib.util.module_from_spec(spec)
sys.modules[spec.name] = module
assert spec.loader is not None
spec.loader.exec_module(module)


class HyperFramesAlignmentTests(unittest.TestCase):
    def test_default_settings_use_local_hyperframes_whisper(self):
        settings = module.settings_from({})
        self.assertEqual(settings["provider"], "hyperframes_whisper")
        self.assertEqual(settings["engine"], "whisper")
        self.assertEqual(settings["model"], "small.en")
        self.assertEqual(settings["language"], "en")

    def test_parse_flat_hyperframes_word_array(self):
        words = module.parse_hyperframes_words(
            [
                {"text": "Hello", "start": 0.12, "end": 0.44},
                {"text": "world", "start": 0.48, "end": 0.92},
            ],
            duration_ms=1000,
            language="en",
        )
        self.assertEqual(words[0]["start_ms"], 120)
        self.assertEqual(words[1]["end_ms"], 920)
        self.assertEqual(words[1]["text"], "world")

    def test_parse_dict_words_and_clamp_end(self):
        words = module.parse_hyperframes_words(
            {"words": [{"text": "end", "start": 0.9, "end": 1.4}]},
            duration_ms=1000,
            language="en",
        )
        self.assertEqual(words[0]["end_ms"], 1000)

    def test_reference_coverage_gate(self):
        timed = [{"text": "x"}] * 8
        ok, ratio = module.coverage_ok(timed, "one two three four five six seven eight nine ten", 0.72)
        self.assertTrue(ok)
        self.assertAlmostEqual(ratio, 0.8)

        ok, ratio = module.coverage_ok(timed[:5], "one two three four five six seven eight nine ten", 0.72)
        self.assertFalse(ok)
        self.assertAlmostEqual(ratio, 0.5)


if __name__ == "__main__":
    unittest.main()
