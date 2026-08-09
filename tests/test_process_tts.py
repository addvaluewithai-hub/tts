import importlib.util
import tempfile
import unittest
import sys
from pathlib import Path


# Allow pure unit tests to run even in environments where google-genai is not installed.
try:
    import google.genai  # noqa: F401
except ImportError:
    import types
    google_mod = sys.modules.setdefault("google", types.ModuleType("google"))
    genai_mod = types.ModuleType("google.genai")
    errors_mod = types.ModuleType("google.genai.errors")

    class APIError(Exception):
        pass

    errors_mod.APIError = APIError
    genai_mod.errors = errors_mod
    genai_mod.Client = object
    google_mod.genai = genai_mod
    sys.modules["google.genai"] = genai_mod
    sys.modules["google.genai.errors"] = errors_mod

MODULE_PATH = Path(__file__).resolve().parents[1] / "scripts" / "process_tts.py"
spec = importlib.util.spec_from_file_location("process_tts", MODULE_PATH)
process_tts = importlib.util.module_from_spec(spec)
sys.modules[spec.name] = process_tts
assert spec.loader is not None
spec.loader.exec_module(process_tts)


class ProcessTtsTests(unittest.TestCase):
    def test_front_matter(self):
        metadata, body = process_tts.parse_front_matter(
            "---\nvoice: Puck\ndirector_notes: Excited\n---\nHello world"
        )
        self.assertEqual(metadata["voice"], "Puck")
        self.assertEqual(body, "Hello world")

    def test_plain_transcript(self):
        metadata, body = process_tts.parse_front_matter("Hello world")
        self.assertEqual(metadata, {})
        self.assertEqual(body, "Hello world")

    def test_split_transcript_respects_limit(self):
        text = ("First sentence. Second sentence. Third sentence. " * 20).strip()
        chunks = process_tts.split_transcript(text, max_chars=120)
        self.assertGreater(len(chunks), 1)
        self.assertTrue(all(len(chunk) <= 120 for chunk in chunks))

    def test_multi_speaker_config(self):
        config = {"voice": "Kore"}
        metadata = {
            "speakers": [
                {"speaker": "Maya", "voice": "Kore"},
                {"speaker": "Leo", "voice": "Puck"},
            ]
        }
        speech = process_tts.normalize_speech_config(config, metadata)
        self.assertEqual(speech[1], {"speaker": "Leo", "voice": "Puck"})

    def test_discover_jobs_ignores_gitkeep(self):
        with tempfile.TemporaryDirectory() as tmp:
            inbox = Path(tmp)
            (inbox / ".gitkeep").write_text("", encoding="utf-8")
            (inbox / "hello.txt").write_text("Hello", encoding="utf-8")
            jobs = process_tts.discover_jobs(inbox)
            self.assertEqual(len(jobs), 1)
            self.assertEqual(jobs[0].relative_path, Path("hello.txt"))


if __name__ == "__main__":
    unittest.main()
