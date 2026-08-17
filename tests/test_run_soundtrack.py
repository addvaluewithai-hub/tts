import importlib.util
import tempfile
import unittest
from pathlib import Path

MODULE_PATH = Path(__file__).resolve().parents[1] / "scripts" / "run_soundtrack.py"
spec = importlib.util.spec_from_file_location("run_soundtrack", MODULE_PATH)
run_soundtrack = importlib.util.module_from_spec(spec)
assert spec.loader is not None
spec.loader.exec_module(run_soundtrack)


class PublicRepoSfxLicenseTests(unittest.TestCase):
    def make_job(self, root: Path, *, redistribution=None):
        (root / "ACTIVE").write_text("lesson-01\n", encoding="utf-8")
        job = root / "lesson-01"
        (job / "sfx").mkdir(parents=True)
        (job / "job.yaml").write_text(
            """schema: 1
id: lesson-01
soundtrack:
  enabled: true
  sfx:
    enabled: true
    events:
      - file: click.wav
        at_ms: 100
""",
            encoding="utf-8",
        )
        redistribution_line = "" if redistribution is None else f"    redistribution: {str(redistribution).lower()}\n"
        (job / "sfx" / "manifest.yaml").write_text(
            "files:\n"
            "  click.wav:\n"
            "    source_url: https://example.com/click\n"
            "    license: Creative Commons CC0\n"
            + redistribution_line,
            encoding="utf-8",
        )

    def test_rejects_missing_redistribution_permission(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            self.make_job(root)
            with self.assertRaises(run_soundtrack.SfxLicenseError):
                run_soundtrack.validate_public_repo_sfx(root)

    def test_rejects_false_redistribution_permission(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            self.make_job(root, redistribution=False)
            with self.assertRaises(run_soundtrack.SfxLicenseError):
                run_soundtrack.validate_public_repo_sfx(root)

    def test_accepts_explicit_redistribution_permission(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            self.make_job(root, redistribution=True)
            run_soundtrack.validate_public_repo_sfx(root)

    def test_no_active_job_is_noop(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            (root / "ACTIVE").write_text("# none\n", encoding="utf-8")
            run_soundtrack.validate_public_repo_sfx(root)


if __name__ == "__main__":
    unittest.main()
