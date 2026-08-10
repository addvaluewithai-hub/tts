import importlib.util
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch


MODULE_PATH = Path(__file__).resolve().parents[1] / "scripts" / "ingest_input.py"
spec = importlib.util.spec_from_file_location("ingest_input", MODULE_PATH)
ingest_input = importlib.util.module_from_spec(spec)
sys.modules[spec.name] = ingest_input
assert spec.loader is not None
spec.loader.exec_module(ingest_input)


class IngestInputTests(unittest.TestCase):
    def test_read_active_ignores_comments(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "ACTIVE"
            path.write_text("# comment\n\nlesson-02\n", encoding="utf-8")
            self.assertEqual(ingest_input.read_active(path), "lesson-02")

    def test_changed_input_is_queued(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            input_root = root / "input"
            job = input_root / "lesson-02"
            transcript = job / "transcript"
            transcript.mkdir(parents=True)
            (input_root / "ACTIVE").write_text("lesson-02\n", encoding="utf-8")
            (job / "job.yaml").write_text("schema: 1\nid: lesson-02\n", encoding="utf-8")
            (transcript / "01-intro.txt").write_text("Hello", encoding="utf-8")

            with patch.object(
                sys,
                "argv",
                [
                    "ingest_input.py",
                    "--input-root", str(input_root),
                    "--queue-root", str(root / "transcripts"),
                    "--done-root", str(root / "done"),
                ],
            ):
                self.assertEqual(ingest_input.main(), 0)

            queued = root / "transcripts" / "lesson-02" / "01-intro.txt"
            self.assertTrue(queued.exists())
            self.assertEqual(queued.read_text(encoding="utf-8"), "Hello")

    def test_completed_identical_input_is_not_requeued(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            input_root = root / "input"
            job = input_root / "lesson-02"
            transcript = job / "transcript"
            transcript.mkdir(parents=True)
            (input_root / "ACTIVE").write_text("lesson-02\n", encoding="utf-8")
            (job / "job.yaml").write_text("schema: 1\nid: lesson-02\n", encoding="utf-8")
            (transcript / "01-intro.txt").write_text("Hello", encoding="utf-8")
            done_dir = root / "done" / "lesson-02"
            done_dir.mkdir(parents=True)
            (done_dir / "01-intro.txt").write_text("Hello", encoding="utf-8")

            with patch.object(
                sys,
                "argv",
                [
                    "ingest_input.py",
                    "--input-root", str(input_root),
                    "--queue-root", str(root / "transcripts"),
                    "--done-root", str(root / "done"),
                ],
            ):
                self.assertEqual(ingest_input.main(), 0)

            self.assertFalse((root / "transcripts" / "lesson-02" / "01-intro.txt").exists())

    def test_removing_completed_part_fails_safely(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            input_root = root / "input"
            job = input_root / "lesson-02"
            transcript = job / "transcript"
            transcript.mkdir(parents=True)
            (input_root / "ACTIVE").write_text("lesson-02\n", encoding="utf-8")
            (job / "job.yaml").write_text("schema: 1\nid: lesson-02\n", encoding="utf-8")
            (transcript / "01-intro.txt").write_text("Hello", encoding="utf-8")
            done_dir = root / "done" / "lesson-02"
            done_dir.mkdir(parents=True)
            (done_dir / "01-intro.txt").write_text("Hello", encoding="utf-8")
            (done_dir / "02-old.txt").write_text("Old", encoding="utf-8")

            with patch.object(
                sys,
                "argv",
                [
                    "ingest_input.py",
                    "--input-root", str(input_root),
                    "--queue-root", str(root / "transcripts"),
                    "--done-root", str(root / "done"),
                ],
            ):
                self.assertEqual(ingest_input.main(), 2)


if __name__ == "__main__":
    unittest.main()
