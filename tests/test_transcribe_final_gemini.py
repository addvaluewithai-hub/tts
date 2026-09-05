import importlib.util
import sys
import unittest
from pathlib import Path

MODULE_PATH = Path(__file__).resolve().parents[1] / "scripts" / "transcribe_final_gemini.py"
spec = importlib.util.spec_from_file_location("transcribe_final_gemini", MODULE_PATH)
module = importlib.util.module_from_spec(spec)
sys.modules[spec.name] = module
assert spec.loader is not None
spec.loader.exec_module(module)


class GeminiMasterAlignmentTests(unittest.TestCase):
    def test_defaults_use_single_master_transcriber(self):
        settings = module.settings_from({})
        self.assertEqual(settings["model"], "gemini-3.5-transcribe")
        self.assertEqual(settings["language_codes"], ["en-US"])
        self.assertGreaterEqual(settings["max_delay_seconds"], 60)

    def test_retry_delay_uses_provider_hint(self):
        exc = RuntimeError("Quota exceeded. Please retry in 47.979s.")
        self.assertAlmostEqual(module.retry_delay_from_error(exc), 47.979)

    def test_words_for_part_converts_global_offsets_to_relative(self):
        part = {"start_ms": 1000, "end_ms": 2000, "duration_ms": 1000}
        raw = [
            {"start_ms": 200, "end_ms": 500, "text": "before", "language": "en"},
            {"start_ms": 1100, "end_ms": 1300, "text": "hello", "language": "en"},
            {"start_ms": 1600, "end_ms": 1900, "text": "world", "language": "en"},
            {"start_ms": 2200, "end_ms": 2400, "text": "after", "language": "en"},
        ]
        selected = module.words_for_part(raw, part)
        self.assertEqual([item["text"] for item in selected], ["hello", "world"])
        self.assertEqual(selected[0]["start_ms"], 100)
        self.assertEqual(selected[1]["end_ms"], 900)

    def test_build_alignment_preserves_zero_based_segment_index(self):
        parts = [
            {"file": "01.wav", "start_ms": 0, "end_ms": 1000, "duration_ms": 1000},
            {"file": "02.wav", "start_ms": 1300, "end_ms": 2300, "duration_ms": 1000},
        ]
        raw = [
            {"start_ms": 100, "end_ms": 300, "text": "hello", "language": "en"},
            {"start_ms": 400, "end_ms": 700, "text": "world", "language": "en"},
            {"start_ms": 1400, "end_ms": 1600, "text": "second", "language": "en"},
            {"start_ms": 1700, "end_ms": 2100, "text": "part", "language": "en"},
        ]
        refs = {"01": "hello world", "02": "second part"}
        settings = {"model": "gemini-3.5-transcribe", "min_reference_coverage": 0.72}
        enriched, segments, words = module.build_part_alignment(
            parts=parts,
            raw_words=raw,
            references=refs,
            settings=settings,
        )
        self.assertEqual(len(enriched), 2)
        self.assertEqual(len(segments), 2)
        self.assertEqual([w["segment_index"] for w in words], [0, 0, 1, 1])
        self.assertEqual(words[2]["start_ms"], 1400)

    def test_number_format_difference_keeps_canonical_anchor(self):
        raw = [
            {"start_ms": 0, "end_ms": 120, "text": "one", "language": "en"},
            {"start_ms": 120, "end_ms": 260, "text": "hundred", "language": "en"},
            {"start_ms": 260, "end_ms": 400, "text": "eighty", "language": "en"},
            {"start_ms": 420, "end_ms": 600, "text": "seats", "language": "en"},
        ]
        canonical, _ = module.canonicalize_to_reference(raw, "180 seats", duration_ms=1000)
        self.assertEqual(canonical[0]["text"], "180")
        self.assertEqual(canonical[-1]["text"], "seats")
        self.assertLess(canonical[0]["start_ms"], canonical[0]["end_ms"])


if __name__ == "__main__":
    unittest.main()
