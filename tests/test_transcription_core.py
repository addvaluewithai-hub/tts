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

    def test_clean_reference_removes_silent_markup(self):
        text = """---
voice: Sulafat
---
[WARM] أهلًا <lang xml:lang="en-US"><phoneme alphabet="ipa" ph="haɪ">Hi</phoneme></lang>
"""
        self.assertEqual(core.clean_reference_text(text), "أهلًا Hi")

    def test_part_timeline_uses_gap(self):
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
                    {"file": "01.wav", "start_ms": 0, "end_ms": 1000},
                    {"file": "02.wav", "start_ms": 1300, "end_ms": 1800},
                ],
            )

    def test_normalize_payload(self):
        payload = {
            "segments": [
                {
                    "start_ms": 0,
                    "end_ms": 1000,
                    "speaker": "Teacher",
                    "language": "ar",
                    "text": "أهلًا",
                }
            ],
            "words": [
                {
                    "start_ms": 100,
                    "end_ms": 700,
                    "text": "أهلًا",
                    "language": "ar",
                    "segment_index": 0,
                }
            ],
        }
        result = core.normalize_payload(payload, 1000)
        self.assertEqual(result["words"][0]["text"], "أهلًا")

    def test_existing_matches_requires_hashes(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "lesson.transcript.json"
            path.write_text(
                json.dumps(
                    {
                        "audio_sha256": "audio",
                        "transcription_config_sha256": "config",
                        "words": [{"text": "hello"}],
                    }
                ),
                encoding="utf-8",
            )
            self.assertTrue(core.existing_matches(path, "audio", "config"))
            self.assertFalse(core.existing_matches(path, "changed", "config"))

    def test_vtt_format(self):
        text = core.render_vtt(
            [{"start_ms": 1234, "end_ms": 5678, "text": "Hello"}]
        )
        self.assertIn("00:00:01.234 --> 00:00:05.678", text)


if __name__ == "__main__":
    unittest.main()
