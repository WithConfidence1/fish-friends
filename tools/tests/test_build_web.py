import json
import unittest
from pathlib import Path

from tools.build_web import (
    BUNDLE,
    REFERENCE,
    extract_block,
    extract_embedded_body,
    extract_embedded_open_tag,
    extract_open_tag,
    extract_script,
    splice,
)

ROOT = Path(__file__).resolve().parents[2]


class TestBuildWeb(unittest.TestCase):
    def test_extract_finds_single_game_script(self):
        body = extract_script(REFERENCE.read_text(encoding="utf-8"))
        self.assertIn("class Component extends DCLogic", body)
        self.assertIn("startRound()", body)

    def test_extract_block_includes_open_tag_and_body(self):
        ref_text = REFERENCE.read_text(encoding="utf-8")
        block = extract_block(ref_text)
        open_tag = extract_open_tag(ref_text)
        body = extract_script(ref_text)
        self.assertTrue(block.startswith(open_tag))
        self.assertEqual(block, open_tag + body)

    def test_bundle_embeds_reference_script(self):
        # After a build, unescaping the bundle's embedded body yields the
        # reference body byte-for-byte.
        ref_text = REFERENCE.read_text(encoding="utf-8")
        ref_body = extract_script(ref_text)
        ref_block = extract_block(ref_text)
        bundle = BUNDLE.read_text(encoding="utf-8")
        built = splice(bundle, ref_block)
        embedded = extract_embedded_body(built)
        self.assertEqual(json.loads('"%s"' % embedded), ref_body)

    def test_splice_syncs_open_tag_data_props(self):
        # After a build, unescaping the bundle's embedded open tag yields
        # the reference's open tag (data-props included) byte-for-byte —
        # this is what makes settings like the `pace` default and the
        # `level` enum's options actually reach the shipped bundle.
        ref_text = REFERENCE.read_text(encoding="utf-8")
        ref_open_tag = extract_open_tag(ref_text)
        ref_block = extract_block(ref_text)
        bundle = BUNDLE.read_text(encoding="utf-8")
        built = splice(bundle, ref_block)
        embedded_open_tag = extract_embedded_open_tag(built)
        self.assertEqual(json.loads('"%s"' % embedded_open_tag), ref_open_tag)

    def test_stale_open_tag_alone_is_detected(self):
        # Simulate a bundle whose body already matches the reference but
        # whose open tag (data-props) is stale — `--check` must still call
        # this `stale`, i.e. splicing it again must change the text.
        ref_text = REFERENCE.read_text(encoding="utf-8")
        ref_block = extract_block(ref_text)
        bundle = BUNDLE.read_text(encoding="utf-8")
        synced = splice(bundle, ref_block)

        old_tag = extract_embedded_open_tag(synced)
        corrupted_tag = old_tag.replace("data-props", "data-props-stale", 1)
        self.assertNotEqual(corrupted_tag, old_tag)  # sanity: corruption took effect
        corrupted = synced.replace(old_tag, corrupted_tag, 1)

        # Only the open tag differs; the body is untouched.
        self.assertEqual(extract_embedded_body(corrupted), extract_embedded_body(synced))
        self.assertNotEqual(corrupted, synced)

        # A `--check` run compares `splice(bundle_text, ref_block) ==
        # bundle_text`; with only the open tag stale, this must be False
        # (i.e. `--check` would print "stale"), and re-splicing must
        # restore the fully-synced bundle.
        rebuilt = splice(corrupted, ref_block)
        self.assertNotEqual(rebuilt, corrupted)
        self.assertEqual(rebuilt, synced)

    def test_splice_is_idempotent(self):
        ref_block = extract_block(REFERENCE.read_text(encoding="utf-8"))
        bundle = BUNDLE.read_text(encoding="utf-8")
        once = splice(bundle, ref_block)
        self.assertEqual(once, splice(once, ref_block))

    def test_splice_rejects_zero_markers(self):
        with self.assertRaises(SystemExit):
            splice("no markers here", "x = 1")

    def test_splice_rejects_multiple_markers(self):
        one_tag = '<script type=\\"text/x-dc\\" data-dc-script\\">'
        two = one_tag + "body one<\\u002Fscript>" + one_tag + "body two<\\u002Fscript>"
        with self.assertRaises(SystemExit):
            splice(two, "x = 1")


if __name__ == "__main__":
    unittest.main()
