import importlib.util
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

MODULE_PATH = Path(__file__).resolve().parents[1] / "scripts" / "run_factory.py"
spec = importlib.util.spec_from_file_location("run_factory", MODULE_PATH)
run_factory = importlib.util.module_from_spec(spec)
assert spec.loader is not None
spec.loader.exec_module(run_factory)


class RunFactoryTests(unittest.TestCase):
    @patch.object(run_factory.subprocess, "run")
    def test_run_stage_uses_repository_root(self, mocked_run):
        mocked_run.return_value.returncode = 0
        result = run_factory.run_stage("tts", Path("tts_config.yaml"))
        self.assertEqual(result, 0)
        command = mocked_run.call_args.args[0]
        self.assertEqual(command[0], sys.executable)
        self.assertTrue(command[1].endswith("scripts/process_tts.py"))
        self.assertEqual(command[-2:], ["--config", "tts_config.yaml"])
        self.assertEqual(mocked_run.call_args.kwargs["cwd"], run_factory.ROOT)

    def test_canonicalize_done_promotes_latest_retake(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            done = root / "done"
            lesson = done / "lesson"
            lesson.mkdir(parents=True)
            canonical = lesson / "01-intro.txt"
            canonical.write_text("old", encoding="utf-8")
            older = lesson / "01-intro-20260809T100000Z.txt"
            older.write_text("middle", encoding="utf-8")
            newest = lesson / "01-intro-20260809T110000Z.txt"
            newest.write_text("new", encoding="utf-8")

            self.assertEqual(run_factory.canonicalize_done(done), 1)
            self.assertEqual(canonical.read_text(encoding="utf-8"), "new")
            self.assertFalse(older.exists())
            self.assertFalse(newest.exists())

    @patch.object(run_factory, "canonicalize_done")
    @patch.object(run_factory, "run_stage")
    @patch.object(sys, "argv", ["run_factory.py"])
    def test_main_runs_stages_in_order(self, mocked_stage, mocked_canonicalize):
        mocked_stage.return_value = 0
        self.assertEqual(run_factory.main(), 0)
        self.assertEqual(
            [call.args[0] for call in mocked_stage.call_args_list],
            ["tts", "assemble", "align"],
        )
        mocked_canonicalize.assert_called_once_with(run_factory.ROOT / "done")

    @patch.object(run_factory, "canonicalize_done")
    @patch.object(run_factory, "run_stage")
    @patch.object(sys, "argv", ["run_factory.py"])
    def test_main_stops_after_failure(self, mocked_stage, mocked_canonicalize):
        mocked_stage.side_effect = [0, 7]
        self.assertEqual(run_factory.main(), 7)
        self.assertEqual(
            [call.args[0] for call in mocked_stage.call_args_list],
            ["tts", "assemble"],
        )
        mocked_canonicalize.assert_called_once_with(run_factory.ROOT / "done")


if __name__ == "__main__":
    unittest.main()
