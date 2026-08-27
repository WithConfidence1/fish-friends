import unittest
from pathlib import Path

from tools.voicelib import slug, parse_voice_md, game_lines, ffmpeg_args, NUMBER_WORDS

VOICE_MD = Path(__file__).resolve().parents[2] / "docs" / "VOICE.md"


class TestSlug(unittest.TestCase):
    def test_matches_game_examples(self):
        self.assertEqual(slug("one"), "one")
        self.assertEqual(slug("Can you count the orange fish?"),
                         "can-you-count-the-orange-fish")
        self.assertEqual(slug("four! 4 orange fish! Hooray!"),
                         "four-4-orange-fish-hooray")
        self.assertEqual(slug("Six treats shared with three fish... two each! Fair sharing, hooray!"),
                         "six-treats-shared-with-three-fish-two-each-fair-sharing-hooray")

    def test_truncates_at_80(self):
        self.assertEqual(len(slug("x" * 200)), 80)


class TestParseVoiceMd(unittest.TestCase):
    def test_exactly_108_rows(self):
        self.assertEqual(len(parse_voice_md(VOICE_MD)), 108)

    def test_every_filename_is_slug_of_text(self):
        for row in parse_voice_md(VOICE_MD):
            self.assertEqual(slug(row.text) + ".mp3", row.filename, row.text)

    def test_rows_carry_section_and_tone(self):
        rows = parse_voice_md(VOICE_MD)
        numbers = [r for r in rows if r.section.startswith("Numbers")]
        self.assertEqual(len(numbers), 10)
        self.assertTrue(all(r.tone for r in rows))


class TestGameLines(unittest.TestCase):
    def test_every_reachable_game_line_has_a_clip_row(self):
        voice_slugs = {r.filename[:-4] for r in parse_voice_md(VOICE_MD)}
        missing = {slug(t) for t in game_lines()} - voice_slugs
        self.assertEqual(missing, set())

    def test_enumeration_size(self):
        self.assertEqual(len({slug(t) for t in game_lines()}), 104)


class TestFfmpegArgs(unittest.TestCase):
    def test_number_clips_are_trimmed_tight(self):
        args = ffmpeg_args("in.mp3", "out.mp3", tight=True)
        joined = " ".join(args)
        self.assertIn("silenceremove", joined)
        self.assertNotIn("adelay", joined)

    def test_sentence_clips_get_padding(self):
        joined = " ".join(ffmpeg_args("in.mp3", "out.mp3", tight=False))
        self.assertIn("adelay", joined)
        self.assertIn("apad", joined)


if __name__ == "__main__":
    unittest.main()
