import importlib.util
import tempfile
import unittest
import wave
import sys
from pathlib import Path

MODULE_PATH = Path(__file__).resolve().parents[1] / "scripts" / "assemble_lessons.py"
spec = importlib.util.spec_from_file_location("assemble_lessons", MODULE_PATH)
assemble_lessons = importlib.util.module_from_spec(spec)
sys.modules[spec.name] = assemble_lessons
assert spec.loader is not None
spec.loader.exec_module(assemble_lessons)


def write_wav(path: Path, frames: int, rate: int = 24_000) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with wave.open(str(path), "wb") as wf:
        wf.setnchannels(1)
        wf.setsampwidth(2)
        wf.setframerate(rate)
        wf.writeframes(b"\x01\x00" * frames)


class AssembleLessonTests(unittest.TestCase):
    def test_discovers_and_sorts_lesson_parts(self):
        with tempfile.TemporaryDirectory() as tmp:
            audio = Path(tmp) / "audio"
            write_wav(audio / "lesson-a" / "02-second.wav", 10)
            write_wav(audio / "lesson-a" / "01-first.wav", 10)
            lessons = assemble_lessons.discover_lessons(audio)
            self.assertEqual(list(lessons), [Path("lesson-a")])
            self.assertEqual(
                [path.name for path in lessons[Path("lesson-a")]],
                ["01-first.wav", "02-second.wav"],
            )

    def test_assembles_wav_with_gap(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            first = root / "01.wav"
            second = root / "02.wav"
            output = root / "final.wav"
            write_wav(first, 2_400)
            write_wav(second, 2_400)

            audio_format, total_frames = assemble_lessons.assemble_wav(
                [first, second], output, gap_ms=300
            )
            self.assertEqual(audio_format.frame_rate, 24_000)
            self.assertEqual(total_frames, 12_000)
            with wave.open(str(output), "rb") as wf:
                self.assertEqual(wf.getnframes(), 12_000)

    def test_rejects_mixed_wav_formats(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            first = root / "01.wav"
            second = root / "02.wav"
            write_wav(first, 100, rate=24_000)
            write_wav(second, 100, rate=16_000)
            with self.assertRaises(assemble_lessons.AssemblyError):
                assemble_lessons.assemble_wav(
                    [first, second], root / "final.wav", gap_ms=0
                )


if __name__ == "__main__":
    unittest.main()
