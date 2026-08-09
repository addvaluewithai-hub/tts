import importlib.util
import json
import sys
import tempfile
import types
import unittest
import wave
from pathlib import Path

try:
    import google.genai  # noqa: F401
except ImportError:
    google_mod = sys.modules.setdefault("google", types.ModuleType("google"))
    genai_mod = types.ModuleType("google.genai")
    errors_mod = types.ModuleType("google.genai.errors")

    class APIError(Exception):
        pass

    errors_mod.APIError = APIError
    genai_mod.Client = object
    genai_mod.errors = errors_mod
    google_mod.genai = genai_mod
    sys.modules["google.genai"] = genai_mod
    sys.modules["google.genai.errors"] = errors_mod

MODULE = Path(__file__).resolve().parents[1] / "scripts" / "transcription_core.py"
spec = importlib.util.spec_from_file_location("transcription_core", MODULE)
core = importlib.util.module_from_spec(spec)
sys.modules[spec.name] = core
assert spec.loader is not None
spec.loader.exec_module(core)


def write_wav(path: Path, duration_ms: int) -> None:
    frames = round(24_000 * duration_ms / 1000)
    with wave.open(str(path), "wb") as wf:
        wf.setnchannels(1)
        wf.setsampwidth(2)
        wf.setframerate(24_000)
        wf.writeframes(b"\0\0" * frames)


class TranscriptionCoreTests(unittest.TestCase):
    def test_route_rotates_models(self):
        models = ["a", "b"]
        self.assertEqual(core.route_order(models, 0), ["a", "b"])
        self.assertEqual(core.route_order(models, 1), ["b", "a"])
        self.assertEqual(core.route_order(models, 2), ["a", "b"])

    def test_clean_reference_removes_silent_markup_and_speaker_label(self):
        text = """---
voice: Sulafat
---
Speaker 1: [WARM] أهلًا <lang xml:lang="en-US"><phoneme alphabet="ipa" ph="haɪ">Hi</phoneme></lang>
"""
        self.assertEqual(core.clean_reference_text(text), "أهلًا Hi")

    def test_part_timeline_uses_gap_and_duration(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            lesson_dir = root / "lesson"
            lesson_dir.mkdir()
            write_wav(lesson_dir / "01.wav", 1000)
            write_wav(lesson_dir / "02.wav", 500)
            timeline = core.part_timeline(root, Path("lesson"), 300)
            self.assertEqual(
                timeline,
                [
                    {
                        "file": "01.wav",
                        "start_ms": 0,
                        "end_ms": 1000,
                        "duration_ms": 1000,
                    },
                    {
                        "file": "02.wav",
                        "start_ms": 1300,
                        "end_ms": 1800,
                        "duration_ms": 500,
                    },
                ],
            )

    def test_normalize_part_payload(self):
        payload = {
            "text": "أهلًا Hi",
            "language": "mixed",
            "words": [
                {"start_ms": 0, "end_ms": 400, "text": "أهلًا", "language": "ar"},
                {"start_ms": 500, "end_ms": 900, "text": "Hi", "language": "en"},
            ],
        }
        result = core.normalize_part_payload(payload, 1000, expected_words=2)
        self.assertEqual(len(result["words"]), 2)
        self.assertEqual(result["words"][1]["text"], "Hi")

    def test_normalize_rejects_grouped_phrase(self):
        payload = {
            "text": "Tell me",
            "language": "en",
            "words": [
                {"start_ms": 0, "end_ms": 900, "text": "Tell me", "language": "en"}
            ],
        }
        with self.assertRaises(core.TranscriptionError):
            core.normalize_part_payload(payload, 1000, expected_words=2)

    def test_normalize_rejects_incomplete_word_list(self):
        payload = {
            "text": "one two three four five six seven eight nine ten",
            "language": "en",
            "words": [
                {"start_ms": 0, "end_ms": 100, "text": "one", "language": "en"},
                {"start_ms": 100, "end_ms": 200, "text": "two", "language": "en"},
            ],
        }
        with self.assertRaises(core.TranscriptionError):
            core.normalize_part_payload(payload, 1000, expected_words=10)

    def test_cache_and_final_match_require_schema_v2(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            cache = root / "part.timing.json"
            final = root / "lesson.transcript.json"
            data = {
                "schema_version": 2,
                "audio_sha256": "audio",
                "transcription_config_sha256": "config",
                "words": [{"text": "hello"}],
            }
            cache.write_text(json.dumps(data), encoding="utf-8")
            final.write_text(json.dumps(data), encoding="utf-8")
            self.assertIsNotNone(core.load_part_cache(cache, "audio", "config"))
            self.assertTrue(core.existing_matches(final, "audio", "config"))

            data["schema_version"] = 1
            final.write_text(json.dumps(data), encoding="utf-8")
            self.assertFalse(core.existing_matches(final, "audio", "config"))

    def test_vtt_format(self):
        text = core.render_vtt(
            [{"start_ms": 1234, "end_ms": 5678, "text": "Hello"}]
        )
        self.assertIn("00:00:01.234 --> 00:00:05.678", text)


if __name__ == "__main__":
    unittest.main()
