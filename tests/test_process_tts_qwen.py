import importlib.util
import io
import os
import sys
import tempfile
import unittest
import wave
from pathlib import Path
from unittest.mock import patch


MODULE_PATH = Path(__file__).resolve().parents[1] / "scripts" / "process_tts_qwen.py"
spec = importlib.util.spec_from_file_location("process_tts_qwen", MODULE_PATH)
process_tts_qwen = importlib.util.module_from_spec(spec)
sys.modules[spec.name] = process_tts_qwen
assert spec.loader is not None
spec.loader.exec_module(process_tts_qwen)


class ProcessTtsQwenTests(unittest.TestCase):
    def test_sanitize_removes_performance_cues_and_tags(self):
        source = "[CURIOUS, DRY] Hello <lang xml:lang='en'>world</lang>.\n\n[PAUSE] Again."
        self.assertEqual(process_tts_qwen.sanitize_transcript(source), "Hello world.\n\nAgain.")

    def test_split_respects_qwen_limit(self):
        text = ("First sentence. Second sentence. Third sentence. " * 100).strip()
        chunks = process_tts_qwen.split_transcript(text, max_chars=500)
        self.assertGreater(len(chunks), 1)
        self.assertTrue(all(len(chunk) <= 500 for chunk in chunks))

    def test_base_url_uses_environment(self):
        with patch.dict(os.environ, {"QWEN_TTS_API_URL": "https://example.modal.run/"}, clear=False):
            self.assertEqual(
                process_tts_qwen.qwen_base_url({}),
                "https://example.modal.run",
            )

    def test_modal_proxy_header_format(self):
        with patch.dict(
            os.environ,
            {
                "MODAL_PROXY_TOKEN_ID": "wk-test",
                "MODAL_PROXY_TOKEN_SECRET": "ws-secret",
            },
            clear=False,
        ):
            self.assertEqual(
                process_tts_qwen.qwen_headers()["Authorization"],
                "Bearer wk-test.ws-secret",
            )

    def test_concat_wavs_preserves_format(self):
        def make_wav(frames: int) -> bytes:
            out = io.BytesIO()
            with wave.open(out, "wb") as wf:
                wf.setnchannels(1)
                wf.setsampwidth(2)
                wf.setframerate(24000)
                wf.writeframes(b"\x00\x00" * frames)
            return out.getvalue()

        joined = process_tts_qwen.concat_wavs([make_wav(100), make_wav(200)], gap_ms=100)
        meta = process_tts_qwen.validate_wav(joined)
        self.assertEqual(meta["sample_rate_hz"], 24000)
        self.assertEqual(meta["channels"], 1)
        self.assertEqual(meta["frames"], 100 + 200 + 2400)

    def test_discover_jobs_reads_front_matter(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            (root / "01-test.txt").write_text(
                "---\nspeaker: Aiden\n---\nHello world",
                encoding="utf-8",
            )
            jobs = process_tts_qwen.discover_jobs(root)
            self.assertEqual(len(jobs), 1)
            self.assertEqual(jobs[0].metadata["speaker"], "Aiden")
            self.assertEqual(jobs[0].transcript, "Hello world")


if __name__ == "__main__":
    unittest.main()
