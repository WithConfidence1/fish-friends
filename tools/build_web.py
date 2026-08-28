"""Splice the readable reference game source into the shipped web bundle.

`reference/Tap and Count.dc.html` is the readable, hand-edited source of
truth for the game (a design-canvas document). `web/index.html` is the
generated bundle that actually ships: a small loader plus the ENTIRE
reference document embedded as one JSON string literal on the loader's
`<script>` line, with asset/script URLs remapped to opaque ids.

Bundle encoding, as found in `web/index.html`:

  * The whole reference document (from `<!DOCTYPE html>` through
    `</html>`) is embedded as a double-quoted JSON string literal.
  * Inside that string, standard JSON escaping applies (`"` -> `\\"`,
    newlines -> `\\n`, etc) EXCEPT non-ASCII characters, which are left as
    literal UTF-8 rather than `\\uXXXX`-escaped (i.e. the bundler's escaper
    behaves like `json.dumps(..., ensure_ascii=False)`, not the default).
    Forward slashes are also left unescaped on their own (`json.dumps`
    already does this by default).
  * In ADDITION, every literal `</` inside the embedded document is
    escaped to `<\\u002F` (e.g. `</script>` -> `<\\u002Fscript>`,
    `</div>` -> `<\\u002Fdiv>`). This keeps the outer `<script>` tag that
    holds the JSON string from being terminated early by an embedded
    `</script>`.
  * Asset/script src URLs are remapped from relative paths (e.g.
    `./support.js`) to opaque ids, but this remapping does NOT touch the
    game `<script type="text/x-dc" data-dc-script ...>` block's body: the
    body embedded in the bundle is, once JSON-unescaped, byte-for-byte
    identical to the reference's script body. That equivalence is what
    this module's round-trip test enforces, and what later tasks rely on
    when they edit the reference and re-run this build step.

This module finds that script body in both files and splices the
reference's (live, human-edited) body into the bundle's embedded copy,
re-applying the same escaping the bundle already uses.
"""

import argparse
import json
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
REFERENCE = ROOT / "reference" / "Tap and Count.dc.html"
BUNDLE = ROOT / "web" / "index.html"

# The reference document's script tag is plain HTML: attribute values use
# `&quot;` for embedded quotes, so the tag itself never contains a raw `>`
# before the one that closes it.
_REF_OPEN_RE = re.compile(r'<script\s+type="text/x-dc"[^>]*data-dc-script[^>]*>')
_REF_CLOSE = "</script>"

# The bundle's copy of that same open tag, JSON-escaped: `"` -> `\"`. Like
# the reference tag, it contains no raw `>` before the one that closes it.
_BUNDLE_OPEN_RE = re.compile(r'<script type=\\"text/x-dc\\"[^>]*data-dc-script[^>]*\\">')
# `</script>` as it appears once `</` -> `<\u002F` escaping has been applied.
_BUNDLE_CLOSE = "<\\u002Fscript>"


def extract_script(html_text: str) -> str:
    """Return the game script body from a reference-style HTML document.

    The body is the text between the `<script type="text/x-dc"
    data-dc-script ...>` open tag's `>` and its matching `</script>`.
    Exits with an error if the open tag is missing or ambiguous.
    """
    matches = list(_REF_OPEN_RE.finditer(html_text))
    if len(matches) != 1:
        sys.exit(
            "extract_script: expected exactly one "
            '<script type="text/x-dc" ... data-dc-script ...> open tag, '
            f"found {len(matches)}"
        )
    body_start = matches[0].end()
    close_idx = html_text.find(_REF_CLOSE, body_start)
    if close_idx == -1:
        sys.exit("extract_script: no matching </script> close tag found")
    return html_text[body_start:close_idx]


def _find_embedded_region(bundle_text: str) -> tuple[int, int]:
    """Return (body_start, close_idx) bracketing the escaped script body
    embedded in a bundle-style document. Exits with an error if the escaped
    open marker is missing, ambiguous, or has no matching close marker."""
    matches = list(_BUNDLE_OPEN_RE.finditer(bundle_text))
    if len(matches) != 1:
        sys.exit(
            "build_web: expected exactly one embedded "
            '<script type="text/x-dc" ... data-dc-script ...> marker in the '
            f"bundle, found {len(matches)}"
        )
    body_start = matches[0].end()
    close_idx = bundle_text.find(_BUNDLE_CLOSE, body_start)
    if close_idx == -1:
        sys.exit("build_web: no matching escaped </script> close marker found in the bundle")
    return body_start, close_idx


def extract_embedded_body(bundle_text: str) -> str:
    """Return the still-JSON-escaped script body embedded in a bundle-style
    document (the raw text between the escaped open and close markers,
    before JSON-unescaping)."""
    body_start, close_idx = _find_embedded_region(bundle_text)
    return bundle_text[body_start:close_idx]


def splice(bundle_text: str, new_body: str) -> str:
    """Return `bundle_text` with its embedded game script body replaced by
    `new_body`, re-escaped the way the bundle expects: JSON-escaped (minus
    the surrounding quotes), with every `</` additionally escaped to
    `<\\u002F`. Exits with an error if the bundle's embedded script markers
    are missing or ambiguous."""
    body_start, close_idx = _find_embedded_region(bundle_text)
    escaped_body = json.dumps(new_body, ensure_ascii=False)[1:-1].replace("</", "<\\u002F")
    return bundle_text[:body_start] + escaped_body + bundle_text[close_idx:]


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--check",
        action="store_true",
        help="check whether the bundle is stale without writing it",
    )
    args = parser.parse_args(argv)

    ref_body = extract_script(REFERENCE.read_text(encoding="utf-8"))
    bundle_text = BUNDLE.read_text(encoding="utf-8")
    built = splice(bundle_text, ref_body)

    if args.check:
        if built == bundle_text:
            print("clean")
            return 0
        print("stale")
        return 1

    if built == bundle_text:
        print("unchanged")
        return 0
    BUNDLE.write_text(built, encoding="utf-8")
    print("built")
    return 0


if __name__ == "__main__":
    sys.exit(main())
