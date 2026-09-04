import unittest
from pathlib import Path

from tools.generate_voice import (plan_jobs, spoken, PRONUNCIATIONS,
                                  SECTION_SETTINGS, DEFAULT_SETTINGS,
                                  AUDITION_VOICES, MODEL_FILES)

VOICE_MD = Path(__file__).resolve().parents[2] / "docs" / "VOICE.md"


class TestPlanJobs(unittest.TestCase):
    def test_plans_all_151_clips(self):
        jobs = plan_jobs(VOICE_MD)
        self.assertEqual(len(jobs), 151)

    def test_number_words_are_tight(self):
        jobs = {j.filename: j for j in plan_jobs(VOICE_MD)}
        self.assertTrue(jobs["one.mp3"].tight)
        self.assertFalse(jobs["can-you-count-the-orange-fish.mp3"].tight)

    def test_only_filter(self):
        jobs = plan_jobs(VOICE_MD, only={"one", "two"})
        self.assertEqual({j.filename for j in jobs}, {"one.mp3", "two.mp3"})

    def test_every_job_has_voice_settings(self):
        for j in plan_jobs(VOICE_MD):
            self.assertIn("speed", j.settings)

    def test_numbers_are_full_speed_sentences_unhurried(self):
        jobs = {j.filename: j for j in plan_jobs(VOICE_MD)}
        self.assertEqual(jobs["one.mp3"].settings["speed"], 1.0)
        self.assertEqual(
            jobs["can-you-count-the-orange-fish.mp3"].settings["speed"], 0.95)

    def test_section_settings_are_a_subset_of_real_sections(self):
        from tools.voicelib import parse_voice_md
        sections = {r.section for r in parse_voice_md(VOICE_MD)}
        for key in SECTION_SETTINGS:
            self.assertIn(key, sections)

    def test_no_elevenlabs_remnants(self):
        import inspect
        import tools.generate_voice as gv
        src = inspect.getsource(gv)
        self.assertNotIn("elevenlabs", src.lower())
        self.assertNotIn("api-key", src.lower())

    def test_audition_voices_are_kokoro_names(self):
        for name in AUDITION_VOICES:
            self.assertRegex(name, r"^[ab]f_[a-z]+$")

    def test_module_imports_without_kokoro_installed(self):
        # The suite itself runs under system Python with no kokoro-onnx;
        # reaching this line proves the import at the top of the file
        # (and via the other tests) did not pull in the model runtime.
        import sys
        self.assertNotIn("kokoro_onnx", sys.modules)

    def test_model_files_are_versioned_pair(self):
        self.assertEqual(len(MODEL_FILES), 2)
        self.assertTrue(MODEL_FILES[0].endswith(".onnx"))
        self.assertTrue(MODEL_FILES[1].endswith(".bin"))


class TestSpoken(unittest.TestCase):
    """espeak reads "hooray" as HAW-ray (hˈɔːɹeɪ). The synth text gets a
    spelling Kokoro says as hoo-RAY; VOICE.md, slugs and filenames keep
    the real word."""

    def test_hooray_is_respelled_for_the_synth(self):
        self.assertEqual(spoken("three! 3 orange fish! Hooray!"),
                         "three! 3 orange fish! Hurray!")

    def test_lowercase_hooray_keeps_its_case(self):
        self.assertEqual(spoken("Fair sharing, hooray!"),
                         "Fair sharing, hurray!")

    def test_lines_without_overrides_are_untouched(self):
        for line in ("Can you count the orange fish?", "three",
                     "Wow! A new friend is joining our tank!"):
            self.assertEqual(spoken(line), line)

    def test_overrides_are_whole_words_only(self):
        self.assertEqual(spoken("hoorays"), "hoorays")

    def test_override_keys_are_lowercase_words(self):
        for k in PRONUNCIATIONS:
            self.assertRegex(k, r"^[a-z]+$")

    def test_jobs_keep_the_real_line_for_slugs_and_review(self):
        jobs = {j.filename: j for j in plan_jobs(VOICE_MD)}
        j = jobs["three-3-orange-fish-hooray.mp3"]
        self.assertEqual(j.text, "three! 3 orange fish! Hooray!")


if __name__ == "__main__":
    unittest.main()
