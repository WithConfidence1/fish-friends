import json
import unittest
from pathlib import Path

from tools.build_web import BUNDLE, REFERENCE, extract_embedded_body, extract_script, splice

ROOT = Path(__file__).resolve().parents[2]


class TestBuildWeb(unittest.TestCase):
    def test_extract_finds_single_game_script(self):
        body = extract_script(REFERENCE.read_text(encoding="utf-8"))
        self.assertIn("class Component extends DCLogic", body)
        self.assertIn("startRound()", body)

    def test_bundle_embeds_reference_script(self):
        # After a build, unescaping the bundle's embedded body yields the
        # reference body byte-for-byte.
        ref_body = extract_script(REFERENCE.read_text(encoding="utf-8"))
        bundle = BUNDLE.read_text(encoding="utf-8")
        built = splice(bundle, ref_body)
        embedded = extract_embedded_body(built)
        self.assertEqual(json.loads('"%s"' % embedded), ref_body)

    def test_splice_is_idempotent(self):
        ref_body = extract_script(REFERENCE.read_text(encoding="utf-8"))
        bundle = BUNDLE.read_text(encoding="utf-8")
        once = splice(bundle, ref_body)
        self.assertEqual(once, splice(once, ref_body))

    def test_splice_rejects_ambiguous_markers(self):
        with self.assertRaises(SystemExit):
            splice("no markers here", "x = 1")


if __name__ == "__main__":
    unittest.main()
