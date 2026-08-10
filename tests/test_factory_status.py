import importlib.util
import json
import sys
import tempfile
import unittest
from pathlib import Path


MODULE_PATH = Path(__file__).resolve().parents[1] / "scripts" / "factory_status.py"
spec = importlib.util.spec_from_file_location("factory_status", MODULE_PATH)
factory_status = importlib.util.module_from_spec(spec)
sys.modules[spec.name] = factory_status
assert spec.loader is not None
spec.loader.exec_module(factory_status)


class FactoryStatusTests(unittest.TestCase):
    def test_no_active_job(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            (root / "input").mkdir()
            (root / "input" / "ACTIVE").write_text("# none\n", encoding="utf-8")
            status = factory_status.build_status(root)
            self.assertIsNone(status["active_job"])
            self.assertEqual(status["next_action"], "set_active_job")

    def test_ready_audio_but_missing_video_source(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            job = "lesson-02"
            job_dir = root / "input" / job
            (job_dir / "transcript").mkdir(parents=True)
            (root / "input" / "ACTIVE").write_text(job + "\n", encoding="utf-8")
            (job_dir / "job.yaml").write_text(f"schema: 1\nid: {job}\n", encoding="utf-8")
            (job_dir / "direction.md").write_text("Direction", encoding="utf-8")
            (job_dir / "transcript" / "01-intro.txt").write_text("Hello", encoding="utf-8")
            final = root / "final"
            final.mkdir()
            for suffix in ["wav", "mp3", "json", "transcript.json"]:
                (final / f"{job}.{suffix}").write_bytes(b"x")

            status = factory_status.build_status(root)
            self.assertTrue(status["audio"]["complete"])
            self.assertFalse(status["video"]["source_exists"])
            self.assertEqual(status["next_action"], "author_video_source_from_direction_and_timing")

    def test_complete_production(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            job = "lesson-02"
            job_dir = root / "input" / job
            (job_dir / "transcript").mkdir(parents=True)
            (root / "input" / "ACTIVE").write_text(job + "\n", encoding="utf-8")
            (job_dir / "job.yaml").write_text(f"schema: 1\nid: {job}\n", encoding="utf-8")
            (job_dir / "direction.md").write_text("Direction", encoding="utf-8")
            (job_dir / "transcript" / "01-intro.txt").write_text("Hello", encoding="utf-8")
            final = root / "final"
            final.mkdir()
            for suffix in ["wav", "mp3", "json", "transcript.json"]:
                (final / f"{job}.{suffix}").write_bytes(b"x")

            project = root / "productions" / job / "video" / "scripts"
            project.mkdir(parents=True)
            (project / "build-from-audio.mjs").write_text("", encoding="utf-8")
            approval = root / "approvals" / job
            approval.mkdir(parents=True)
            (approval / "APPROVED").write_text("ok", encoding="utf-8")
            status_dir = root / ".factory-status" / "video" / job
            status_dir.mkdir(parents=True)
            (status_dir / "qa-latest.json").write_text(json.dumps({
                "lint_outcome": "success",
                "check_outcome": "success",
                "inspect_outcome": "success",
                "draft_outcome": "success",
                "run_id": "1",
            }), encoding="utf-8")
            (status_dir / "final-status.json").write_text(json.dumps({"status": "complete"}), encoding="utf-8")
            (status_dir / "final-latest.json").write_text(json.dumps({"run_id": "2", "artifact_url": "x"}), encoding="utf-8")

            status = factory_status.build_status(root)
            self.assertEqual(status["next_action"], "production_ready")


if __name__ == "__main__":
    unittest.main()
