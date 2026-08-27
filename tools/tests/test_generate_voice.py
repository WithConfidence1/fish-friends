import unittest
from pathlib import Path

from tools.generate_voice import plan_jobs, SECTION_SETTINGS, DEFAULT_SETTINGS

VOICE_MD = Path(__file__).resolve().parents[2] / "docs" / "VOICE.md"


class TestPlanJobs(unittest.TestCase):
    def test_plans_all_108_clips(self):
        jobs = plan_jobs(VOICE_MD)
        self.assertEqual(len(jobs), 108)

    def test_number_words_are_tight(self):
        jobs = {j.filename: j for j in plan_jobs(VOICE_MD)}
        self.assertTrue(jobs["one.mp3"].tight)
        self.assertFalse(jobs["can-you-count-the-orange-fish.mp3"].tight)

    def test_only_filter(self):
        jobs = plan_jobs(VOICE_MD, only={"one", "two"})
        self.assertEqual({j.filename for j in jobs}, {"one.mp3", "two.mp3"})

    def test_every_job_has_voice_settings(self):
        for j in plan_jobs(VOICE_MD):
            self.assertIn("stability", j.settings)

    def test_section_settings_are_a_subset_of_real_sections(self):
        from tools.voicelib import parse_voice_md
        sections = {r.section for r in parse_voice_md(VOICE_MD)}
        for key in SECTION_SETTINGS:
            self.assertIn(key, sections)


if __name__ == "__main__":
    unittest.main()
