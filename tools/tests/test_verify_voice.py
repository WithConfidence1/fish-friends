import tempfile
import unittest
from pathlib import Path

from tools.verify_voice import check

VOICE_MD = Path(__file__).resolve().parents[2] / "docs" / "VOICE.md"


class TestCheck(unittest.TestCase):
    def test_pending_mode_passes_with_empty_voice_dir(self):
        with tempfile.TemporaryDirectory() as d:
            code, report = check(Path(d), VOICE_MD, strict=False)
        self.assertEqual(code, 0)
        self.assertIn("151 missing", report)

    def test_strict_mode_fails_with_empty_voice_dir(self):
        with tempfile.TemporaryDirectory() as d:
            code, report = check(Path(d), VOICE_MD, strict=True)
        self.assertEqual(code, 1)

    def test_strict_mode_passes_when_all_clips_exist(self):
        with tempfile.TemporaryDirectory() as d:
            from tools.voicelib import parse_voice_md
            for row in parse_voice_md(VOICE_MD):
                (Path(d) / row.filename).write_bytes(b"fake mp3")
            code, report = check(Path(d), VOICE_MD, strict=True)
        self.assertEqual(code, 0)

    def test_unexpected_file_fails_even_in_pending_mode(self):
        with tempfile.TemporaryDirectory() as d:
            (Path(d) / "not-a-known-line.mp3").write_bytes(b"x")
            code, report = check(Path(d), VOICE_MD, strict=False)
        self.assertEqual(code, 1)
        self.assertIn("not-a-known-line.mp3", report)


if __name__ == "__main__":
    unittest.main()
