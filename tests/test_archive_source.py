import importlib.util
import sys
import tempfile
import types
import unittest
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
    genai_mod.errors = errors_mod
    genai_mod.Client = object
    google_mod.genai = genai_mod
    sys.modules["google.genai"] = genai_mod
    sys.modules["google.genai.errors"] = errors_mod

MODULE_PATH = Path(__file__).resolve().parents[1] / "scripts" / "process_tts.py"
spec = importlib.util.spec_from_file_location("process_tts_archive", MODULE_PATH)
process_tts = importlib.util.module_from_spec(spec)
sys.modules[spec.name] = process_tts
assert spec.loader is not None
spec.loader.exec_module(process_tts)


class ArchiveSourceTests(unittest.TestCase):
    def test_latest_success_replaces_canonical_done_transcript(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            inbox = root / "transcripts"
            done = root / "done"
            source = inbox / "lesson" / "01-intro.txt"
            source.parent.mkdir(parents=True)
            source.write_text("new transcript", encoding="utf-8")

            canonical = done / "lesson" / "01-intro.txt"
            canonical.parent.mkdir(parents=True)
            canonical.write_text("old transcript", encoding="utf-8")

            job = process_tts.TranscriptJob(
                source_path=source,
                relative_path=Path("lesson/01-intro.txt"),
                transcript="new transcript",
                metadata={},
            )
            archived = process_tts.archive_source(job, done)

            self.assertEqual(archived, canonical)
            self.assertEqual(canonical.read_text(encoding="utf-8"), "new transcript")
            self.assertFalse(source.exists())


if __name__ == "__main__":
    unittest.main()
