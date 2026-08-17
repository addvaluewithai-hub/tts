import importlib.util
import tempfile
import unittest
from pathlib import Path

MODULE_PATH = Path(__file__).resolve().parents[1] / "scripts" / "run_soundtrack.py"
spec = importlib.util.spec_from_file_location("run_soundtrack", MODULE_PATH)
run_soundtrack = importlib.util.module_from_spec(spec)
assert spec.loader is not None
spec.loader.exec_module(run_soundtrack)


class ZeroCostPolicyTests(unittest.TestCase):
    def write_policy(self, root: Path, paid: bool = False) -> Path:
        policy = root / "factory_policy.yaml"
        policy.write_text(
            "schema: 1\ncost:\n"
            f"  paid_media_generation: {str(paid).lower()}\n"
            "  target_incremental_media_cost_usd: 0\n",
            encoding="utf-8",
        )
        return policy

    def make_music_job(self, root: Path, source: str):
        (root / "ACTIVE").write_text("lesson-01\n", encoding="utf-8")
        job = root / "lesson-01"
        job.mkdir(parents=True)
        (job / "job.yaml").write_text(
            "schema: 1\nid: lesson-01\nsoundtrack:\n  enabled: true\n"
            "  music:\n    enabled: true\n"
            f"    source: {source}\n",
            encoding="utf-8",
        )

    def test_lyria_is_blocked_when_paid_media_is_disabled(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            self.make_music_job(root, "lyria")
            policy = self.write_policy(root, paid=False)
            with self.assertRaises(run_soundtrack.PaidMediaPolicyError):
                run_soundtrack.validate_zero_cost_policy(root, policy)

    def test_local_music_is_allowed_under_zero_cost_policy(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            self.make_music_job(root, "file")
            policy = self.write_policy(root, paid=False)
            run_soundtrack.validate_zero_cost_policy(root, policy)

    def test_no_active_job_is_noop(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            (root / "ACTIVE").write_text("# none\n", encoding="utf-8")
            policy = self.write_policy(root, paid=False)
            run_soundtrack.validate_zero_cost_policy(root, policy)


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
