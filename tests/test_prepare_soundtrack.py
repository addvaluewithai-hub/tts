import importlib.util
import tempfile
import unittest
from pathlib import Path

SPEC = importlib.util.spec_from_file_location(
    "prepare_soundtrack",
    Path(__file__).resolve().parents[1] / "scripts" / "prepare_soundtrack.py",
)
soundtrack = importlib.util.module_from_spec(SPEC)
assert SPEC.loader is not None
SPEC.loader.exec_module(soundtrack)


class SoundtrackTimingTests(unittest.TestCase):
    def setUp(self):
        self.transcript = {
            "duration_ms": 10000,
            "parts": [
                {"file": "01-hook.wav", "start_ms": 0},
                {"file": "02-body.wav", "start_ms": 5000},
            ],
            "words": [
                {"text": "Hello", "start_ms": 100},
                {"text": "world!", "start_ms": 500},
                {"text": "بس", "start_ms": 1200},
                {"text": "كده.", "start_ms": 1500},
                {"text": "Hello", "start_ms": 4000},
                {"text": "world", "start_ms": 4300},
            ],
        }

    def test_resolves_anchor_with_punctuation_and_offset(self):
        self.assertEqual(
            soundtrack.resolve_event_ms(
                {"anchor_text": "بس كده", "offset_ms": 100},
                self.transcript,
            ),
            1300,
        )

    def test_resolves_anchor_occurrence(self):
        self.assertEqual(
            soundtrack.resolve_event_ms(
                {"anchor_text": "Hello world", "occurrence": 2},
                self.transcript,
            ),
            4000,
        )

    def test_resolves_part_and_negative_offset(self):
        self.assertEqual(
            soundtrack.resolve_event_ms(
                {"part": 2, "offset_ms": -200},
                self.transcript,
            ),
            4800,
        )

    def test_resolves_seconds(self):
        self.assertEqual(
            soundtrack.resolve_event_ms({"at_seconds": 2.5}, self.transcript),
            2500,
        )

    def test_missing_anchor_is_error(self):
        with self.assertRaises(soundtrack.SoundtrackError):
            soundtrack.resolve_event_ms(
                {"anchor_text": "does not exist"},
                self.transcript,
            )


class SoundtrackSfxManifestTests(unittest.TestCase):
    def test_sfx_requires_license_traceability(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            (root / "sfx").mkdir()
            (root / "sfx" / "click.wav").write_bytes(b"fake")
            (root / "sfx" / "manifest.yaml").write_text(
                "files:\n  click.wav:\n    source_url: https://example.com/click\n    license: Test License\n",
                encoding="utf-8",
            )
            events = soundtrack.resolve_sfx_events(
                root,
                {
                    "enabled": True,
                    "events": [{"file": "click.wav", "at_ms": 500}],
                },
                {"duration_ms": 1000, "parts": [], "words": []},
                1000,
            )
            self.assertEqual(events[0]["at_ms"], 500)
            self.assertEqual(events[0]["license"], "Test License")

    def test_sfx_missing_manifest_entry_fails(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            (root / "sfx").mkdir()
            (root / "sfx" / "click.wav").write_bytes(b"fake")
            (root / "sfx" / "manifest.yaml").write_text(
                "files: {}\n",
                encoding="utf-8",
            )
            with self.assertRaises(soundtrack.SoundtrackError):
                soundtrack.resolve_sfx_events(
                    root,
                    {
                        "enabled": True,
                        "events": [{"file": "click.wav", "at_ms": 500}],
                    },
                    {"duration_ms": 1000, "parts": [], "words": []},
                    1000,
                )


if __name__ == "__main__":
    unittest.main()
