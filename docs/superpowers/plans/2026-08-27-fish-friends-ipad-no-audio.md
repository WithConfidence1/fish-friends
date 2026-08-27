# Fish Friends iPad (No-Audio Build) Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Ship everything in the approved spec except running the voice batch: restructure the repo, build the voice tooling (ready to run when Taylor supplies his ElevenLabs key), build the SwiftUI WKWebView shell with icon, and verify the app in the iPad Simulator. Robot speech-synthesis fallback is the expected interim voice.

**Architecture:** The game is the self-contained bundled HTML build (`Fish Friends - iPad.html`, already committed as `index.html`). It embeds its own runtime (support.js, React 18.3.1, Baloo 2 woff2 fonts) but loads sprites and voice clips at runtime via relative paths (`assets/kit/*.png`, `assets/voice/*.mp3`). So `web/` holds the bundle plus `assets/`, and a WKWebView loads it with `loadFileURL` granting read access to `web/`. Missing MP3s make the game fall back to `speechSynthesis` per clip, which is exactly the no-audio interim behavior we want.

**Tech Stack:** SwiftUI + WKWebView (iPadOS 16+), XcodeGen 2.46 (installed), Xcode 26.6, Python 3.14 stdlib + Pillow 12.3 (installed), ffmpeg (installed), Python `unittest` (pytest is NOT installed on this machine).

## Global Constraints

- Repo: `~/Code/fish-friends`, branch `main`, one existing commit (`113457b`). Spec at `docs/superpowers/specs/2026-08-26-fish-friends-ipad-design.md`.
- iPad-only target (`TARGETED_DEVICE_FAMILY = 2`), iPadOS deployment target `16.0`, all orientations, full screen, status bar hidden.
- Bundle identifier: `com.taylorernst.fishfriends`. Display name: `Fish Friends`.
- **Never modify the game HTML.** The bundle is the product; the shell adapts around it.
- No App Store / TestFlight. Signing team selection is Taylor's manual step in Xcode.
- Voice audio generation is DEFERRED: write and dry-run-test the generator, never call the ElevenLabs API in this build. `web/assets/voice/` ships empty.
- The game's slug function (verified against all 108 VOICE.md rows, 0 mismatches): lowercase, replace runs of `[^a-z0-9]` with `-`, strip leading/trailing `-`, truncate to 80 chars, append `.mp3`.
- Voice source of truth: `~/Downloads/design_handoff_fish_friends/VOICE.md`, exactly 108 table rows in 16 sections, each section with an italic tone direction line.
- Test simulator device: `iPad Pro 11-inch (M5)` (available in this Xcode).
- Python tests use `unittest` via `python3 -m unittest`, run from repo root.
- No em dashes in any prose file written for this repo.

## Spec Deviation (locked in, documented here)

The spec says `web/index.html` is "renamed from `Tap and Count.dc.html`". That file CANNOT run standalone: it is a design-canvas source that requires a `./support.js` runtime which is not in the handoff. The runnable artifact is the bundled build `Fish Friends - iPad.html` (405,211 bytes, byte-identical to the `index.html` already committed at repo root). Therefore:

- `web/index.html` = the bundled build (moved from repo root).
- `Tap and Count.dc.html` goes to `reference/` as the readable source of every rule and timing constant, alongside an untouched copy of the original bundle.

Verified bundle facts this plan relies on: manifest embeds only support.js + React + ReactDOM + 4 Baloo 2 woff2 files; sprites are fetched at runtime relative to the page (`assets/kit/` appears once in the file, in the dynamic loader); voice fetch is `new Audio('assets/voice/' + slug + '.mp3')` with per-slug fallback to `speechSynthesis`; localStorage keys `tap-count-progress` and `tap-count-treasures` (persistence is a spec non-goal).

## File Structure (end state)

```
~/Code/fish-friends/
  README.md                     Task 7: Taylor-facing status + how to finish audio + install
  .gitignore                    Task 1
  web/
    index.html                  Task 1: the bundled game (moved from repo root)
    assets/kit/*.png            Task 1: 40 sprites copied from handoff
    assets/voice/.gitkeep       Task 1: empty until Taylor runs the batch
  reference/
    Tap and Count.dc.html       Task 1: readable reference implementation
    Fish Friends - iPad.html    Task 1: pristine original bundle
  docs/
    handoff-README.md           Task 1: copied from handoff
    VOICE.md                    Task 1: copied from handoff (parser input)
    superpowers/specs/...       already present
    superpowers/plans/...       this file
  tools/
    voicelib.py                 Task 2: slug, VOICE.md parser, game-line enumeration, ffmpeg args
    verify_voice.py             Task 2: 3-way cross-check CLI (pending / strict modes)
    generate_voice.py           Task 3: ElevenLabs audition + batch CLI (dry-run tested only)
    generate_review.py          Task 3: emits tools/review.html clip audition page
    make_icon.py                Task 5: composes the app icon from the clownfish sprite
    tests/
      __init__.py               Task 2
      test_voicelib.py          Task 2
      test_verify_voice.py      Task 2
      test_generate_voice.py    Task 3
  app/
    project.yml                 Task 4: XcodeGen spec
    FishFriends.xcodeproj       Task 4: generated, committed so Taylor can double-click
    Info.plist                  Task 4: generated by XcodeGen from project.yml info block
    Sources/
      FishFriendsApp.swift      Task 4
      GameWebView.swift         Task 4
    Resources/
      Assets.xcassets/AppIcon.appiconset/
        Contents.json           Task 4 (empty icon), Task 5 (single-size 1024 entry)
        icon-1024.png           Task 5
```

Interfaces used across tasks: `tools/voicelib.py` exposes `slug(text) -> str`, `parse_voice_md(path) -> list[Row]` where `Row = namedtuple('Row', 'text filename section tone')`, `game_lines() -> set[str]` (raw line texts), `NUMBER_WORDS` (list of ten words), and `ffmpeg_args(src, dst, tight: bool) -> list[str]`. `verify_voice.py` exposes `check(voice_dir, voice_md_path, strict: bool) -> tuple[int, str]` returning (exit_code, report). Paths `web/assets/voice`, `docs/VOICE.md`, and the bundle id `com.taylorernst.fishfriends` are fixed vocabulary.

---

### Task 1: Repo restructure (web/, reference/, docs/, .gitignore)

**Files:**
- Move: `index.html` -> `web/index.html`
- Create: `web/assets/kit/` (40 PNGs), `web/assets/voice/.gitkeep`, `reference/`, `docs/handoff-README.md`, `docs/VOICE.md`, `.gitignore`

**Interfaces:**
- Consumes: handoff at `~/Downloads/design_handoff_fish_friends/`
- Produces: the `web/` directory every later task points at; `docs/VOICE.md` consumed by Tasks 2 and 3; `web/assets/kit/fish-orange.png` consumed by Task 5

- [ ] **Step 1: Move and copy files**

```bash
cd ~/Code/fish-friends
git mv index.html web/index.html 2>/dev/null || { mkdir -p web && git mv index.html web/index.html; }
mkdir -p web/assets/voice reference docs
cp -R ~/Downloads/design_handoff_fish_friends/assets/kit web/assets/kit
touch web/assets/voice/.gitkeep
cp ~/Downloads/design_handoff_fish_friends/"Tap and Count.dc.html" reference/
cp ~/Downloads/design_handoff_fish_friends/"Fish Friends - iPad.html" reference/
cp ~/Downloads/design_handoff_fish_friends/README.md docs/handoff-README.md
cp ~/Downloads/design_handoff_fish_friends/VOICE.md docs/VOICE.md
```

- [ ] **Step 2: Write `.gitignore`**

```gitignore
.DS_Store
__pycache__/
app/build/
DerivedData/
xcuserdata/
*.xcuserstate
tools/audition/
```

- [ ] **Step 3: Verify the layout serves correctly**

```bash
cd ~/Code/fish-friends/web && python3 -m http.server 8123 &
sleep 1
curl -s -o /dev/null -w "%{http_code} " http://localhost:8123/index.html
curl -s -o /dev/null -w "%{http_code} " http://localhost:8123/assets/kit/turtle.png
curl -s -o /dev/null -w "%{http_code}\n" http://localhost:8123/assets/kit/fish-orange.png
kill %1
ls web/assets/kit | wc -l
cmp web/index.html reference/"Fish Friends - iPad.html" && echo BUNDLE-IDENTICAL
```

Expected: `200 200 200`, sprite count `40`, `BUNDLE-IDENTICAL`.

- [ ] **Step 4: Commit**

```bash
cd ~/Code/fish-friends
git add -A
git commit -m "chore: restructure repo into web/, reference/, docs/ per spec

Co-Authored-By: Claude Fable 5 <noreply@anthropic.com>"
```

---

### Task 2: Voice library and verification tool (TDD)

**Files:**
- Create: `tools/voicelib.py`, `tools/verify_voice.py`, `tools/tests/__init__.py`, `tools/tests/test_voicelib.py`, `tools/tests/test_verify_voice.py`

**Interfaces:**
- Consumes: `docs/VOICE.md`, `web/assets/voice/` from Task 1
- Produces: `voicelib.slug`, `voicelib.parse_voice_md`, `voicelib.game_lines`, `voicelib.ffmpeg_args`, `voicelib.NUMBER_WORDS`, `verify_voice.check` used by Task 3

Facts already verified on this machine (the tests below encode them): VOICE.md parses to exactly 108 rows; `slug(text) + '.mp3' == filename` for all 108; `game_lines()` enumerates 104 lines, all 104 present in VOICE.md; the 4 VOICE.md extras are addition celebrate lines for (A,B) pairs the level ranges never roll, e.g. `five-one-and-four-makes-5-hooray`. Extras are a warning, not a failure. A game line missing from VOICE.md IS a failure (it means silent robot fallback for a reachable line).

- [ ] **Step 1: Write the failing tests**

`tools/tests/__init__.py`: empty file.

`tools/tests/test_voicelib.py`:

```python
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
```

`tools/tests/test_verify_voice.py`:

```python
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
        self.assertIn("108 missing", report)

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
```

- [ ] **Step 2: Run tests to verify they fail**

```bash
cd ~/Code/fish-friends && python3 -m unittest discover -s tools/tests -t . -v 2>&1 | tail -5
```

Expected: FAIL / ERROR with `ModuleNotFoundError: No module named 'tools.voicelib'`. Note: `tools/` needs no `__init__.py` under Python 3 namespace packages, but if discovery complains, add an empty `tools/__init__.py` and keep going.

- [ ] **Step 3: Write `tools/voicelib.py`**

```python
"""Shared voice-pipeline logic for Fish Friends (Tap and Count).

The slug function is a line-for-line port of say() in the game
(reference/Tap and Count.dc.html); if the game ever changes, change
this to match, never the other way around.
"""
import re
from collections import namedtuple

Row = namedtuple("Row", "text filename section tone")

NUMBER_WORDS = ["one", "two", "three", "four", "five",
                "six", "seven", "eight", "nine", "ten"]


def slug(text):
    return re.sub(r"[^a-z0-9]+", "-", text.lower()).strip("-")[:80]


def parse_voice_md(path):
    """Parse the '| Say this | Save as |' tables plus each section's
    heading and italic tone direction."""
    rows, section, tone = [], "", ""
    for line in open(path, encoding="utf-8"):
        line = line.rstrip("\n")
        m = re.match(r"^##\s+(.*)", line)
        if m:
            section, tone = m.group(1).strip(), ""
            continue
        m = re.match(r"^\*(.+)\*\s*$", line)
        if m and not tone:
            tone = m.group(1).strip()
            continue
        m = re.match(r"^\|\s*(.+?)\s*\|\s*`([^`]+)`\s*\|", line)
        if m and m.group(1) != "Say this":
            rows.append(Row(m.group(1), m.group(2), section, tone))
    return rows


def game_lines():
    """Every line the game can speak, enumerated from the say() call
    sites and the per-level A/B ranges in startRound():
      L1 count N 2..5, L2 count N 6..10
      L3 add A,B 1..3, L4 add A,B 2..5
      L5 sub A 4..8, B 1..A-2
      L6 mul A,B 2..3, L7 div A,B 2..3 (N = A*B)
    """
    W = NUMBER_WORDS
    lines = set(W)  # tap counting and skip counting
    lines.add("Can you count the orange fish?")
    for n in range(2, 11):  # count celebrate
        lines.add(f"{W[n - 1]}! {n} orange fish! Hooray!")

    add_pairs = ({(a, b) for a in range(1, 4) for b in range(1, 4)}
                 | {(a, b) for a in range(2, 6) for b in range(2, 6)})
    sub_pairs = {(a, b) for a in range(4, 9) for b in range(1, a - 1)}

    for a in {p[0] for p in add_pairs} | {p[0] for p in sub_pairs}:
        lines.add(f"Look! {W[a - 1]} orange fish are here.")
    for b in {p[1] for p in add_pairs}:
        lines.add(f"{W[b - 1]} more are coming! How many fish altogether?")
    for a, b in add_pairs:
        n = a + b
        lines.add(f"{W[n - 1]}! {W[a - 1]} and {W[b - 1]} makes {n}! Hooray!")
    for b in {p[1] for p in sub_pairs}:
        verb = "is" if b == 1 else "are"
        lines.add(f"Oh! {W[b - 1]} {verb} swimming away. How many are left?")
    for a, b in sub_pairs:
        n = a - b
        lines.add(f"{W[n - 1]}! {W[a - 1]} take away {W[b - 1]} makes {n}! Hooray!")

    for a in (2, 3):
        for b in (2, 3):
            n = a * b
            lines.add(f"Look! {W[a - 1]} shells. Every shell has {W[b - 1]} pearls!")
            lines.add(f"{W[n - 1]} pearls! {W[a - 1]} groups of {W[b - 1]} makes {n}! Hooray!")
            lines.add(f"{W[n - 1]} yummy treats! Can you share them with the {W[a - 1]} hungry fish?")
            lines.add(f"{W[n - 1]} treats shared with {W[a - 1]} fish... {W[b - 1]} each! Fair sharing, hooray!")

    lines |= {
        "How many pearls altogether? Tap them all!",
        "Tap a fish to give it a treat. Take turns, so it is fair!",
        "I have enough for now! My friend is hungry too!",
        "Can you tap another pearl?",
        "Tap a fish to give it a treat!",
        "Can you find another orange fish? Tap it!",
        "Wow! Look! Our whole tank is changing!",
        "Wow! A new friend is joining our tank!",
    }
    return lines


def ffmpeg_args(src, dst, tight):
    """Post-process per VOICE.md: numbers trimmed with no lead-in
    silence; everything else trimmed then padded ~0.2s each end."""
    trim = ("silenceremove=start_periods=1:start_threshold=-45dB:start_silence=0.02,"
            "areverse,"
            "silenceremove=start_periods=1:start_threshold=-45dB:start_silence=0.02,"
            "areverse")
    af = trim if tight else trim + ",adelay=200:all=1,apad=pad_dur=0.2"
    return ["ffmpeg", "-y", "-hide_banner", "-loglevel", "error",
            "-i", str(src), "-af", af, "-codec:a", "libmp3lame",
            "-b:a", "128k", str(dst)]
```

- [ ] **Step 4: Write `tools/verify_voice.py`**

```python
"""Three-way cross-check: VOICE.md rows vs the slugs the game
generates vs the files in web/assets/voice/.

Pending mode (default, pre-audio): missing clips are reported but OK.
Strict mode (--strict, the build gate once audio exists): any missing
clip fails. Unexpected files and internal mismatches always fail.
"""
import argparse
import sys
from pathlib import Path

if __package__ in (None, ""):
    sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from tools.voicelib import slug, parse_voice_md, game_lines


def check(voice_dir, voice_md_path, strict):
    problems, notes = [], []
    rows = parse_voice_md(voice_md_path)
    if len(rows) != 108:
        problems.append(f"VOICE.md parsed to {len(rows)} rows, expected 108")

    for row in rows:
        if slug(row.text) + ".mp3" != row.filename:
            problems.append(f"VOICE.md mismatch: slug({row.text!r}) != {row.filename}")

    voice_slugs = {r.filename[:-4] for r in rows}
    game_slugs = {slug(t) for t in game_lines()}
    for s in sorted(game_slugs - voice_slugs):
        problems.append(f"game line has no VOICE.md row (silent robot fallback): {s}")
    extras = sorted(voice_slugs - game_slugs)
    if extras:
        notes.append(f"{len(extras)} VOICE.md rows unreachable by the game (harmless): "
                     + ", ".join(extras))

    present = {p.name for p in Path(voice_dir).glob("*.mp3")}
    expected = {r.filename for r in rows}
    missing = sorted(expected - present)
    unexpected = sorted(present - expected)
    for f in unexpected:
        problems.append(f"unexpected file in voice dir: {f}")
    if missing:
        line = f"{len(missing)} missing of {len(expected)} clips"
        if strict:
            problems.append(line)
        else:
            notes.append(line + " (pending mode: OK until the batch runs)")

    report = "\n".join(f"FAIL {p}" for p in problems)
    if notes:
        report += ("\n" if report else "") + "\n".join(f"note {n}" for n in notes)
    if not problems:
        report += "\nOK   voice pipeline consistent"
    return (1 if problems else 0), report.strip()


def main():
    ap = argparse.ArgumentParser()
    root = Path(__file__).resolve().parents[1]
    ap.add_argument("--voice-dir", default=root / "web" / "assets" / "voice", type=Path)
    ap.add_argument("--voice-md", default=root / "docs" / "VOICE.md", type=Path)
    ap.add_argument("--strict", action="store_true")
    args = ap.parse_args()
    code, report = check(args.voice_dir, args.voice_md, args.strict)
    print(report)
    sys.exit(code)


if __name__ == "__main__":
    main()
```

- [ ] **Step 5: Run tests to verify they pass**

```bash
cd ~/Code/fish-friends && python3 -m unittest discover -s tools/tests -t . -v 2>&1 | tail -5
```

Expected: all tests PASS (OK). If `test_enumeration_size` fails, do NOT bend the enumeration to hit 104; recount against the say() call sites in `reference/Tap and Count.dc.html` and fix whichever side is wrong, then update this plan note.

- [ ] **Step 6: Run the CLI against the real (empty) voice dir**

```bash
cd ~/Code/fish-friends && python3 tools/verify_voice.py
```

Expected: exit 0, report includes `108 missing of 108 clips (pending mode: OK until the batch runs)`, a note about 4 unreachable VOICE.md rows, and `OK   voice pipeline consistent`.

- [ ] **Step 7: Commit**

```bash
cd ~/Code/fish-friends
git add tools/
git commit -m "feat: voice library and 3-way verification tool with tests

Co-Authored-By: Claude Fable 5 <noreply@anthropic.com>"
```

---

### Task 3: Voice generator (dry-run only) and review page

**Files:**
- Create: `tools/generate_voice.py`, `tools/generate_review.py`, `tools/tests/test_generate_voice.py`

**Interfaces:**
- Consumes: `voicelib.parse_voice_md`, `voicelib.slug`, `voicelib.ffmpeg_args`, `voicelib.NUMBER_WORDS`, `verify_voice.check`
- Produces: `tools/review.html` (generated file, committed); the two CLIs Taylor runs later

The generator is written and dry-run-tested but NEVER run against the live API in this build (no key, audio deferred). Honest caveat carried into the README: the ElevenLabs call path is untested until audition day; expect one round of tuning, which is what the audition step is for.

- [ ] **Step 1: Write the failing tests**

`tools/tests/test_generate_voice.py`:

```python
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
```

- [ ] **Step 2: Run tests to verify they fail**

```bash
cd ~/Code/fish-friends && python3 -m unittest tools.tests.test_generate_voice -v 2>&1 | tail -3
```

Expected: ERROR, `No module named 'tools.generate_voice'`.

- [ ] **Step 3: Write `tools/generate_voice.py`**

```python
"""Generate the 108 voice clips with ElevenLabs, then post-process
with ffmpeg and verify. Deferred until Taylor supplies his key.

Usage:
  export ELEVENLABS_API_KEY=...
  python3 tools/generate_voice.py audition            # 4 voices x 3 sample lines
  python3 tools/generate_voice.py batch --voice NAME  # all 108 clips
  python3 tools/generate_voice.py batch --voice NAME --only one,two
  add --dry-run to either to print the work without network calls
"""
import argparse
import json
import os
import subprocess
import sys
import tempfile
import urllib.request
from collections import namedtuple
from pathlib import Path

if __package__ in (None, ""):
    sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from tools.voicelib import parse_voice_md, ffmpeg_args, NUMBER_WORDS
from tools.verify_voice import check

ROOT = Path(__file__).resolve().parents[1]
VOICE_DIR = ROOT / "web" / "assets" / "voice"
VOICE_MD = ROOT / "docs" / "VOICE.md"
API = "https://api.elevenlabs.io/v1"
MODEL_ID = "eleven_multilingual_v2"

# Warm female premade voices to audition; resolved by name at runtime.
AUDITION_VOICES = ["Rachel", "Matilda", "Dorothy", "Alice"]
AUDITION_LINES = ["three",
                  "Can you count the orange fish?",
                  "Wow! A new friend is joining our tank!"]

DEFAULT_SETTINGS = {"stability": 0.5, "similarity_boost": 0.75,
                    "style": 0.3, "use_speaker_boost": True}
# Per-section overrides, keyed by exact VOICE.md section heading.
# Tune these at audition time; tone directions live in VOICE.md.
SECTION_SETTINGS = {
    "Numbers (counting taps)": {"stability": 0.6, "style": 0.2},
}

Job = namedtuple("Job", "text filename tight settings tone")


def plan_jobs(voice_md=VOICE_MD, only=None):
    jobs = []
    for row in parse_voice_md(voice_md):
        if only is not None and row.filename[:-4] not in only:
            continue
        settings = {**DEFAULT_SETTINGS, **SECTION_SETTINGS.get(row.section, {})}
        jobs.append(Job(row.text, row.filename,
                        row.filename[:-4] in NUMBER_WORDS, settings, row.tone))
    return jobs


def _api(path, key, payload=None):
    req = urllib.request.Request(API + path,
                                 data=json.dumps(payload).encode() if payload else None,
                                 headers={"xi-api-key": key,
                                          "content-type": "application/json"})
    with urllib.request.urlopen(req, timeout=120) as r:
        return r.read()


def resolve_voice(name, key):
    voices = json.loads(_api("/voices", key))["voices"]
    for v in voices:
        if v["name"].lower() == name.lower():
            return v["voice_id"]
    sys.exit(f"voice {name!r} not found; available: "
             + ", ".join(sorted(v["name"] for v in voices)))


def synth(text, voice_id, settings, key):
    return _api(f"/text-to-speech/{voice_id}?output_format=mp3_44100_128", key,
                {"text": text, "model_id": MODEL_ID, "voice_settings": settings})


def postprocess(raw_mp3_bytes, dst, tight):
    with tempfile.NamedTemporaryFile(suffix=".mp3") as tmp:
        tmp.write(raw_mp3_bytes)
        tmp.flush()
        subprocess.run(ffmpeg_args(tmp.name, dst, tight), check=True)


def cmd_audition(args, key):
    outdir = ROOT / "tools" / "audition"
    for name in AUDITION_VOICES:
        for text in AUDITION_LINES:
            dst = outdir / f"{name.lower()}-{text.split()[0].lower().strip('!')}.mp3"
            if args.dry_run:
                print(f"would synth {name}: {text!r} -> {dst.relative_to(ROOT)}")
                continue
            outdir.mkdir(exist_ok=True)
            vid = resolve_voice(name, key)
            postprocess(synth(text, vid, DEFAULT_SETTINGS, key), dst, tight=False)
            print(f"wrote {dst.relative_to(ROOT)}")
    if not args.dry_run:
        print("\nListen, pick a voice, then run: "
              "python3 tools/generate_voice.py batch --voice NAME")


def cmd_batch(args, key):
    only = set(args.only.split(",")) if args.only else None
    jobs = plan_jobs(only=only)
    if args.dry_run:
        for j in jobs:
            print(f"would synth [{'tight' if j.tight else 'padded'}] "
                  f"{j.filename}: {j.text!r}")
        print(f"{len(jobs)} clips planned")
        return
    vid = resolve_voice(args.voice, key)
    VOICE_DIR.mkdir(parents=True, exist_ok=True)
    for i, j in enumerate(jobs, 1):
        postprocess(synth(j.text, vid, j.settings, key), VOICE_DIR / j.filename, j.tight)
        print(f"[{i}/{len(jobs)}] {j.filename}")
    code, report = check(VOICE_DIR, VOICE_MD, strict=only is None)
    print(report)
    sys.exit(code)


def main():
    ap = argparse.ArgumentParser()
    sub = ap.add_subparsers(dest="cmd", required=True)
    a = sub.add_parser("audition")
    a.add_argument("--dry-run", action="store_true")
    b = sub.add_parser("batch")
    b.add_argument("--voice", help="voice name picked at audition")
    b.add_argument("--only", help="comma-separated slugs to regenerate")
    b.add_argument("--dry-run", action="store_true")
    args = ap.parse_args()
    key = os.environ.get("ELEVENLABS_API_KEY", "")
    if not key and not args.dry_run:
        sys.exit("set ELEVENLABS_API_KEY first (or use --dry-run)")
    if args.cmd == "batch" and not args.dry_run and not args.voice:
        sys.exit("batch needs --voice NAME (run audition first)")
    {"audition": cmd_audition, "batch": cmd_batch}[args.cmd](args, key)


if __name__ == "__main__":
    main()
```

- [ ] **Step 4: Write `tools/generate_review.py`**

```python
"""Emit tools/review.html: every clip with a play button, its line,
section, and tone, plus a reject list Taylor can copy into
generate_voice.py batch --only ... for regeneration."""
import html
import sys
from pathlib import Path

if __package__ in (None, ""):
    sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from tools.voicelib import parse_voice_md

ROOT = Path(__file__).resolve().parents[1]

HEAD = """<!DOCTYPE html><html><head><meta charset="utf-8">
<title>Fish Friends voice review</title>
<style>
body{font-family:-apple-system,sans-serif;margin:2rem;max-width:60rem}
h2{margin:1.6rem 0 .2rem}.tone{color:#666;font-style:italic;margin:0 0 .6rem}
.row{display:flex;align-items:center;gap:.7rem;padding:.25rem 0;border-bottom:1px solid #eee}
.row.missing .line{color:#b00}.line{flex:1}audio{height:2rem}
#rejects{width:100%;height:4rem;margin-top:1rem}
</style></head><body>
<h1>Voice review: 108 clips</h1>
<p>Play everything. Tick the box on any clip that misses
"warm, unhurried, small smile". Red rows are missing files.</p>
"""

TAIL = """<h2>Rejects</h2>
<textarea id="rejects" readonly placeholder="tick boxes above"></textarea>
<p>Regenerate with: <code>python3 tools/generate_voice.py batch --voice NAME
--only &lt;paste list&gt;</code></p>
<script>
document.querySelectorAll('audio').forEach(a=>a.addEventListener('error',
  ()=>a.closest('.row').classList.add('missing')));
const out=document.getElementById('rejects');
document.querySelectorAll('input[type=checkbox]').forEach(c=>
  c.addEventListener('change',()=>{
    out.value=[...document.querySelectorAll('input:checked')]
      .map(c=>c.dataset.slug).join(',');
  }));
</script></body></html>
"""


def main():
    rows = parse_voice_md(ROOT / "docs" / "VOICE.md")
    parts, section = [HEAD], None
    for r in rows:
        if r.section != section:
            section = r.section
            parts.append(f"<h2>{html.escape(section)}</h2>"
                         f"<p class=tone>{html.escape(r.tone)}</p>")
        slug = r.filename[:-4]
        parts.append(
            f'<div class=row><input type=checkbox data-slug="{slug}">'
            f'<audio controls preload=none src="../web/assets/voice/{r.filename}"></audio>'
            f'<span class=line>{html.escape(r.text)}</span>'
            f'<code>{r.filename}</code></div>')
    parts.append(TAIL)
    out = ROOT / "tools" / "review.html"
    out.write_text("\n".join(parts), encoding="utf-8")
    print(f"wrote {out} ({len(rows)} rows)")


if __name__ == "__main__":
    main()
```

- [ ] **Step 5: Run tests, dry-runs, and the review generator**

```bash
cd ~/Code/fish-friends
python3 -m unittest discover -s tools/tests -t . 2>&1 | tail -3
python3 tools/generate_voice.py audition --dry-run
python3 tools/generate_voice.py batch --dry-run | tail -3
python3 tools/generate_review.py
grep -c "class=row" tools/review.html
```

Expected: tests OK; audition dry-run prints 12 `would synth` lines; batch dry-run ends `108 clips planned`; review generator writes `tools/review.html`; grep prints `108`.

- [ ] **Step 6: Commit**

```bash
cd ~/Code/fish-friends
git add tools/
git commit -m "feat: ElevenLabs generator (dry-run tested) and clip review page

Co-Authored-By: Claude Fable 5 <noreply@anthropic.com>"
```

---

### Task 4: Xcode project and SwiftUI WKWebView shell

**Files:**
- Create: `app/project.yml`, `app/Sources/FishFriendsApp.swift`, `app/Sources/GameWebView.swift`, `app/Resources/Assets.xcassets/Contents.json`, `app/Resources/Assets.xcassets/AppIcon.appiconset/Contents.json`
- Generate + commit: `app/FishFriends.xcodeproj`, `app/Info.plist` (both produced by `xcodegen generate`)

**Interfaces:**
- Consumes: `web/` from Task 1 (folder reference copied into the bundle as `web/`)
- Produces: buildable scheme `FishFriends`, bundle id `com.taylorernst.fishfriends`, asset catalog slot `AppIcon` that Task 5 fills

- [ ] **Step 1: Write `app/project.yml`**

```yaml
name: FishFriends
options:
  deploymentTarget:
    iOS: "16.0"
targets:
  FishFriends:
    type: application
    platform: iOS
    sources:
      - path: Sources
      - path: Resources
      - path: ../web
        type: folder
        buildPhase: resources
    info:
      path: Info.plist
      properties:
        CFBundleDisplayName: Fish Friends
        UILaunchScreen: {}
        UIRequiresFullScreen: true
        UIStatusBarHidden: true
        UIViewControllerBasedStatusBarAppearance: false
        UISupportedInterfaceOrientations:
          - UIInterfaceOrientationLandscapeLeft
          - UIInterfaceOrientationLandscapeRight
          - UIInterfaceOrientationPortrait
          - UIInterfaceOrientationPortraitUpsideDown
    settings:
      base:
        PRODUCT_BUNDLE_IDENTIFIER: com.taylorernst.fishfriends
        TARGETED_DEVICE_FAMILY: "2"
        ASSETCATALOG_COMPILER_APPICON_NAME: AppIcon
        CODE_SIGN_STYLE: Automatic
        SWIFT_VERSION: "5.0"
```

- [ ] **Step 2: Write `app/Sources/FishFriendsApp.swift`**

```swift
import SwiftUI
import AVFoundation

@main
struct FishFriendsApp: App {
    @Environment(\.scenePhase) private var scenePhase

    init() {
        // Audible even with the mute switch on, per spec.
        try? AVAudioSession.sharedInstance().setCategory(.playback)
        try? AVAudioSession.sharedInstance().setActive(true)
    }

    var body: some Scene {
        WindowGroup {
            GameWebView()
                .ignoresSafeArea()
                .background(Color.black)
                .statusBarHidden(true)
                .persistentSystemOverlays(.hidden)
        }
        .onChange(of: scenePhase) { phase in
            // Wake lock only while the aquarium is actually up.
            UIApplication.shared.isIdleTimerDisabled = (phase == .active)
        }
    }
}
```

- [ ] **Step 3: Write `app/Sources/GameWebView.swift`**

```swift
import SwiftUI
import WebKit

struct GameWebView: UIViewRepresentable {
    func makeCoordinator() -> Coordinator { Coordinator() }

    func makeUIView(context: Context) -> WKWebView {
        let config = WKWebViewConfiguration()
        config.allowsInlineMediaPlayback = true
        config.mediaTypesRequiringUserActionForPlayback = []

        let webView = WKWebView(frame: .zero, configuration: config)
        webView.navigationDelegate = context.coordinator
        webView.isOpaque = false
        webView.backgroundColor = .black
        webView.scrollView.isScrollEnabled = false
        webView.scrollView.bounces = false
        webView.scrollView.contentInsetAdjustmentBehavior = .never
        webView.allowsLinkPreview = false
        webView.allowsBackForwardNavigationGestures = false

        if let index = Bundle.main.url(forResource: "index",
                                       withExtension: "html",
                                       subdirectory: "web") {
            webView.loadFileURL(index,
                                allowingReadAccessTo: index.deletingLastPathComponent())
        }
        return webView
    }

    func updateUIView(_ webView: WKWebView, context: Context) {
        webView.scrollView.pinchGestureRecognizer?.isEnabled = false
    }

    final class Coordinator: NSObject, WKNavigationDelegate {
        // The web view only ever shows the local game.
        func webView(_ webView: WKWebView,
                     decidePolicyFor navigationAction: WKNavigationAction,
                     decisionHandler: @escaping (WKNavigationActionPolicy) -> Void) {
            decisionHandler(navigationAction.request.url?.isFileURL == true ? .allow : .cancel)
        }
    }
}
```

- [ ] **Step 4: Write the empty asset catalog**

`app/Resources/Assets.xcassets/Contents.json`:

```json
{
  "info" : { "author" : "xcode", "version" : 1 }
}
```

`app/Resources/Assets.xcassets/AppIcon.appiconset/Contents.json` (Task 5 adds the image entry):

```json
{
  "images" : [ ],
  "info" : { "author" : "xcode", "version" : 1 }
}
```

- [ ] **Step 5: Generate the project and build for the iPad Simulator**

```bash
cd ~/Code/fish-friends/app
xcodegen generate
xcodebuild -project FishFriends.xcodeproj -scheme FishFriends \
  -destination 'platform=iOS Simulator,name=iPad Pro 11-inch (M5)' \
  -derivedDataPath build build 2>&1 | tail -5
```

Expected: `** BUILD SUCCEEDED **`. If XcodeGen rejects `buildPhase: resources` on the folder source, drop that line (folder references default to the resources phase) and regenerate.

- [ ] **Step 6: Verify the game shipped inside the .app**

```bash
APP=~/Code/fish-friends/app/build/Build/Products/Debug-iphonesimulator/FishFriends.app
ls "$APP/web/index.html" && ls "$APP/web/assets/kit" | wc -l
```

Expected: index.html present, `40` sprites.

- [ ] **Step 7: Commit**

```bash
cd ~/Code/fish-friends
git add app/ .gitignore
git commit -m "feat: SwiftUI WKWebView shell, XcodeGen project, iPad-only full screen

Co-Authored-By: Claude Fable 5 <noreply@anthropic.com>"
```

---

### Task 5: App icon from the clownfish sprite

**Files:**
- Create: `tools/make_icon.py`, `app/Resources/Assets.xcassets/AppIcon.appiconset/icon-1024.png`
- Modify: `app/Resources/Assets.xcassets/AppIcon.appiconset/Contents.json`

**Interfaces:**
- Consumes: `web/assets/kit/fish-orange.png` from Task 1
- Produces: the `AppIcon` single-size icon the Task 4 catalog slot expects

- [ ] **Step 1: Write `tools/make_icon.py`**

```python
"""App icon: the orange clownfish sprite centered on the game's
water gradient (#A9E4F6 to #2E93C4), flattened opaque, 1024x1024."""
import sys
from pathlib import Path

from PIL import Image

ROOT = Path(__file__).resolve().parents[1]
SIZE = 1024
TOP, BOTTOM = (0xA9, 0xE4, 0xF6), (0x2E, 0x93, 0xC4)


def lerp(a, b, t):
    return tuple(round(a[i] + (b[i] - a[i]) * t) for i in range(3))


def main():
    icon = Image.new("RGB", (SIZE, SIZE))
    px = icon.load()
    for y in range(SIZE):
        row = lerp(TOP, BOTTOM, y / (SIZE - 1))
        for x in range(SIZE):
            px[x, y] = row

    fish = Image.open(ROOT / "web" / "assets" / "kit" / "fish-orange.png").convert("RGBA")
    target_w = int(SIZE * 0.72)
    fish = fish.resize((target_w, int(fish.height * target_w / fish.width)),
                       Image.LANCZOS)
    icon.paste(fish, ((SIZE - fish.width) // 2, (SIZE - fish.height) // 2), fish)

    out = (ROOT / "app" / "Resources" / "Assets.xcassets"
           / "AppIcon.appiconset" / "icon-1024.png")
    icon.save(out, "PNG")
    print(f"wrote {out}")


if __name__ == "__main__":
    main()
```

- [ ] **Step 2: Run it and update Contents.json**

```bash
cd ~/Code/fish-friends && python3 tools/make_icon.py
```

Replace `app/Resources/Assets.xcassets/AppIcon.appiconset/Contents.json` with:

```json
{
  "images" : [
    {
      "filename" : "icon-1024.png",
      "idiom" : "universal",
      "platform" : "ios",
      "size" : "1024x1024"
    }
  ],
  "info" : { "author" : "xcode", "version" : 1 }
}
```

- [ ] **Step 3: Verify the icon file and rebuild**

```bash
cd ~/Code/fish-friends
python3 -c "
from PIL import Image
im = Image.open('app/Resources/Assets.xcassets/AppIcon.appiconset/icon-1024.png')
assert im.size == (1024, 1024) and im.mode == 'RGB', (im.size, im.mode)
print('icon OK: 1024x1024 opaque')"
cd app && xcodebuild -project FishFriends.xcodeproj -scheme FishFriends \
  -destination 'platform=iOS Simulator,name=iPad Pro 11-inch (M5)' \
  -derivedDataPath build build 2>&1 | tail -3
```

Expected: `icon OK: 1024x1024 opaque`, then `** BUILD SUCCEEDED **`.

- [ ] **Step 4: Commit**

```bash
cd ~/Code/fish-friends
git add tools/make_icon.py app/Resources
git commit -m "feat: app icon composed from the clownfish sprite

Co-Authored-By: Claude Fable 5 <noreply@anthropic.com>"
```

---

### Task 6: iPad Simulator verification

**Files:** none created; this is the spec's verification section minus MP3 playback (clips do not exist yet; each spoken line falls back to speechSynthesis, which is correct interim behavior).

**Interfaces:**
- Consumes: built app from Task 5, bundle id `com.taylorernst.fishfriends`

Game facts that drive the choreography below (from the reference implementation): default pace is "quick demo", so a challenge auto-starts about 5 seconds after load with no tap needed; the turtle rests at proportional position (0.10 W, 0.68 H) and can be tapped to start a challenge immediately; during a count round 2 to 5 orange fish gather in an arc around (0.52 W, 0.32 to 0.44 H); each first tap sticks a white number bubble above the fish; after the final count comes about 3 s of celebration, then a treasure falls to the sand. Tap targets are at least 76 px radius, so tapping the visual center of a fish from a screenshot is reliable.

- [ ] **Step 1: Install and launch on the simulator**

Use the iOS Simulator MCP `control` tool if available in the executing session (preferred; `launch` reports the device's point dimensions and screenshots/taps are built in). Call `attach` first if Taylor might be watching. Otherwise fall back to simctl:

```bash
xcrun simctl boot "iPad Pro 11-inch (M5)" 2>/dev/null; sleep 5
APP=~/Code/fish-friends/app/build/Build/Products/Debug-iphonesimulator/FishFriends.app
xcrun simctl install booted "$APP"
xcrun simctl launch booted com.taylorernst.fishfriends
```

Expected: launch prints a PID. Take a screenshot after ~3 s (`control` action `screenshot`, or `xcrun simctl io booted screenshot /tmp/ff-1.png`).

- [ ] **Step 2: Verify full-screen render**

The screenshot must show: water gradient filling the ENTIRE screen (no status bar, no white margins), sand band at the bottom with kelp/coral/starfish, the turtle at the lower left, fish swimming. If the screen is white, read the failure: a white screen with nothing means `loadFileURL` found no index.html (check Step 6 of Task 4); fish missing but water present means sprites did not ship (folder reference broke).

- [ ] **Step 3: Verify a challenge starts and counting works**

Wait ~8 s from launch (quick-demo pace auto-starts a round at 5 s), screenshot again. Expected: orange fish gathered in an arc with a white glow, prompt strip of mini fish icons near the top, turtle moved toward the fish. Then tap the center of each glowing orange fish one at a time (screenshot between taps). Expected per tap: that fish gains a white number bubble with an orange numeral, and the bubble count increments 1, 2, 3... Re-tap one already-counted fish once: its bubble persists and no new number appears (the never-double-count rule).

- [ ] **Step 4: Verify celebration and reward**

After tapping the last glowing fish, wait ~5 s and screenshot. Expected: loop-de-loop fish trails or star/heart particles (celebration), then a treasure item resting on the sand near the chest at the lower right. This confirms the full free -> invite -> count -> celebrate -> reward loop.

- [ ] **Step 5: Verify relaunch**

```bash
xcrun simctl terminate booted com.taylorernst.fishfriends
xcrun simctl launch booted com.taylorernst.fishfriends
```

Screenshot after ~3 s: aquarium renders again (treasure persistence across relaunch is explicitly NOT required by the spec).

- [ ] **Step 6: Record the evidence**

Save the four key screenshots to `docs/verification/2026-08-27/` (free play, challenge with number bubbles, celebration or treasure, relaunch), then commit:

```bash
cd ~/Code/fish-friends
git add docs/verification
git commit -m "test: iPad Simulator verification screenshots

Co-Authored-By: Claude Fable 5 <noreply@anthropic.com>"
```

---

### Task 7: Taylor-facing README and spec status

**Files:**
- Create: `README.md` (repo root)
- Modify: `docs/superpowers/specs/2026-08-26-fish-friends-ipad-design.md` (status line only)

**Interfaces:**
- Consumes: everything above; commands must match the CLIs exactly as built

- [ ] **Step 1: Write `README.md`**

```markdown
# Fish Friends

Cartoon aquarium math game for the iPad, wrapped as a native app.
The game itself is the bundled HTML prototype in `web/`; the Swift
shell in `app/` just gives it full screen, offline, wake lock, and
audio through the mute switch.

## Status (2026-08-27)

- Built and verified in the iPad Simulator: shell, icon, full game loop.
- NOT done yet: the 108 recorded voice lines. Until then the game
  speaks with the built-in robot voice (per-line fallback, by design).
- The ElevenLabs call path is written and dry-run tested but has not
  hit the live API; expect one round of settings tuning at audition.

## Finish the audio (three commands)

    export ELEVENLABS_API_KEY=your-key
    python3 tools/generate_voice.py audition
    # listen to tools/audition/, pick a voice, then:
    python3 tools/generate_voice.py batch --voice Rachel

The batch writes all 108 MP3s into `web/assets/voice/`, post-processes
them with ffmpeg (numbers tight, sentences padded 0.2s), and runs the
strict verifier. Review every clip in `tools/review.html` (open it in
a browser); tick rejects and regenerate just those with
`batch --voice NAME --only slug1,slug2`. Rebuild the app afterward so
the clips ship inside it. To re-record a line yourself later,
overwrite its MP3 in `web/assets/voice/` and rebuild. Nothing else
changes.

## Install on the iPad

1. Open `app/FishFriends.xcodeproj` in Xcode.
2. Target FishFriends -> Signing & Capabilities -> pick your team.
3. Plug in the iPad, select it as the run destination, press Run.
4. Optional: Settings -> Accessibility -> Guided Access to lock her in.

With a paid Apple Developer membership the install lasts a year. With
a free personal team it expires after 7 days, so use the paid team.

## Development

- `app/project.yml` is the source of truth for the Xcode project;
  after changing it run `xcodegen generate` in `app/`.
- `python3 -m unittest discover -s tools/tests -t .` from the repo
  root runs the voice-pipeline tests.
- `python3 tools/verify_voice.py` checks VOICE.md, the game's
  reachable lines, and the files on disk against each other
  (`--strict` once audio exists).
- Never edit `web/index.html`; the readable game source is
  `reference/Tap and Count.dc.html`.
```

- [ ] **Step 2: Update the spec status line**

In `docs/superpowers/specs/2026-08-26-fish-friends-ipad-design.md`, change `Status: Approved pending Taylor's spec review` to `Status: Approved 2026-08-27. Built without audio (see plans/2026-08-27-fish-friends-ipad-no-audio.md); voice batch deferred to Taylor.`

- [ ] **Step 3: Commit**

```bash
cd ~/Code/fish-friends
git add README.md docs/superpowers/specs
git commit -m "docs: root README with audio and install runbooks; spec status

Co-Authored-By: Claude Fable 5 <noreply@anthropic.com>"
```
