# Kokoro Voice Backend Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Replace the never-used ElevenLabs backend in `tools/generate_voice.py` with local, free Kokoro TTS so the 108 voice clips can be generated on this Mac with no API key or subscription.

**Architecture:** Only `tools/generate_voice.py` changes (plus its test file and docs). The script keeps its exact CLI (`audition`, `batch --voice NAME [--only ...]`, `--dry-run`) but synthesizes with `kokoro-onnx` locally instead of calling an HTTP API. Everything downstream — `voicelib.parse_voice_md`, `ffmpeg_args` post-processing, `verify_voice.check`, `tools/review.html`, the game itself — is untouched. Output is still MP3s in `web/assets/voice/`.

**Tech Stack:** Python 3.12 via `uv` (PEP 723 inline script metadata — system Python is 3.14, which PyTorch/onnxruntime don't support yet), `kokoro-onnx` (CPU inference, no PyTorch), `soundfile` (WAV encoding), existing `ffmpeg` post-processing.

## Global Constraints

- Never edit `web/index.html`; the readable game source is `reference/Tap and Count.dc.html`.
- `docs/VOICE.md` is the source of truth for lines/filenames — do not modify it.
- The unit tests must keep running under **system Python 3.14 with no new packages installed**: `python3 -m unittest discover -s tools/tests -t .` from the repo root. Therefore `kokoro_onnx` and `soundfile` may only be imported lazily (inside functions), never at module top level.
- Voice direction (from VOICE.md): warm, unhurried, never sped up. Default `speed` 0.95; Numbers section 1.0 (clips play rapid-fire).
- Model files (~340MB total) live in `tools/models/`, gitignored, auto-downloaded on first real run.
- CLI shape is frozen: `audition`, `batch --voice NAME`, `--only slug1,slug2`, `--dry-run`. Dry-run must not require the model, network, or `uv`-managed deps.
- Baseline: 18 tests pass before this work; the suite must pass after every task.

---

### Task 1: Retarget voice settings from ElevenLabs knobs to Kokoro speed

**Files:**
- Modify: `tools/tests/test_generate_voice.py` (tests at lines 23-31)
- Modify: `tools/generate_voice.py:39-45` (`DEFAULT_SETTINGS`, `SECTION_SETTINGS`)

**Interfaces:**
- Consumes: `plan_jobs(voice_md, only=None)` (unchanged), module constants `DEFAULT_SETTINGS`, `SECTION_SETTINGS`.
- Produces: every `Job.settings` dict is `{"speed": float}`. Task 2's `synth` reads `settings["speed"]`.

- [ ] **Step 1: Update the settings tests to expect Kokoro's `speed` knob**

In `tools/tests/test_generate_voice.py`, replace the `test_every_job_has_voice_settings` method with:

```python
    def test_every_job_has_voice_settings(self):
        for j in plan_jobs(VOICE_MD):
            self.assertIn("speed", j.settings)

    def test_numbers_are_full_speed_sentences_unhurried(self):
        jobs = {j.filename: j for j in plan_jobs(VOICE_MD)}
        self.assertEqual(jobs["one.mp3"].settings["speed"], 1.0)
        self.assertEqual(
            jobs["can-you-count-the-orange-fish.mp3"].settings["speed"], 0.95)
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `cd /Users/taylorernst/Code/fish-friends && python3 -m unittest tools.tests.test_generate_voice -v`
Expected: FAIL — `'speed'` not found in settings (both new tests fail; others pass).

- [ ] **Step 3: Replace the settings constants**

In `tools/generate_voice.py`, replace lines 39-45 (the `DEFAULT_SETTINGS` and `SECTION_SETTINGS` block, comments included) with:

```python
DEFAULT_SETTINGS = {"speed": 0.95}  # VOICE.md: never sped up
# Per-section overrides, keyed by exact VOICE.md section heading.
# Numbers play rapid-fire as she taps, so keep them at full speed.
SECTION_SETTINGS = {
    "Numbers (counting taps)": {"speed": 1.0},
}
```

- [ ] **Step 4: Run the full suite to verify it passes**

Run: `cd /Users/taylorernst/Code/fish-friends && python3 -m unittest discover -s tools/tests -t .`
Expected: PASS (19 tests — one net new).

- [ ] **Step 5: Commit**

```bash
cd /Users/taylorernst/Code/fish-friends
git add tools/generate_voice.py tools/tests/test_generate_voice.py
git commit -m "feat: retarget voice settings to Kokoro speed knob"
```

---

### Task 2: Swap the synthesis backend from ElevenLabs to local Kokoro

**Files:**
- Modify: `tools/generate_voice.py` (everything except the constants Task 1 wrote and `plan_jobs`)
- Test: `tools/tests/test_generate_voice.py`

**Interfaces:**
- Consumes: `Job.settings["speed"]` from Task 1; `ffmpeg_args(src, dst, tight)` and `check(voice_dir, voice_md, strict)` unchanged from `tools/voicelib.py` / `tools/verify_voice.py`.
- Produces: `synth(text, voice, settings) -> bytes` (WAV bytes), `resolve_voice(name) -> str` (exits with available-voice list if unknown), `ensure_model() -> None`, `engine() -> Kokoro`, `AUDITION_VOICES` (list of Kokoro voice names). `cmd_audition(args)` / `cmd_batch(args)` no longer take a `key` parameter. Module import must succeed with no kokoro-onnx installed.

- [ ] **Step 1: Write the failing tests for the new module surface**

Append to the `TestPlanJobs` class in `tools/tests/test_generate_voice.py` (and extend the import line at the top of the file):

```python
from tools.generate_voice import (plan_jobs, SECTION_SETTINGS, DEFAULT_SETTINGS,
                                  AUDITION_VOICES, MODEL_FILES)
```

```python
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
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `cd /Users/taylorernst/Code/fish-friends && python3 -m unittest tools.tests.test_generate_voice -v`
Expected: FAIL at import — `cannot import name 'AUDITION_VOICES'` (it currently holds ElevenLabs names, but `MODEL_FILES` does not exist).

- [ ] **Step 3: Rewrite `tools/generate_voice.py` with the Kokoro backend**

Replace the entire file with (note: `DEFAULT_SETTINGS`/`SECTION_SETTINGS` are exactly what Task 1 wrote):

```python
# /// script
# requires-python = ">=3.12,<3.13"
# dependencies = [
#     "kokoro-onnx>=0.4.9",
#     "soundfile>=0.12",
# ]
# ///
"""Generate the 108 voice clips locally with Kokoro, then post-process
with ffmpeg and verify. Free and offline; no API key needed.

Usage:
  uv run tools/generate_voice.py audition             # 6 voices x 3 sample lines
  uv run tools/generate_voice.py batch --voice NAME   # all 108 clips
  uv run tools/generate_voice.py batch --voice NAME --only one,two
  add --dry-run to either to print the work without loading the model

First real run downloads ~340MB of Kokoro model files into tools/models/.
"""
import argparse
import io
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
MODEL_DIR = ROOT / "tools" / "models"
MODEL_BASE = ("https://github.com/thewh1teagle/kokoro-onnx/releases/"
              "download/model-files-v1.0/")
MODEL_FILES = ["kokoro-v1.0.onnx", "voices-v1.0.bin"]

# Warm female voices to audition, per VOICE.md's direction.
AUDITION_VOICES = ["af_heart", "af_bella", "af_nicole",
                   "af_sarah", "af_sky", "bf_emma"]
AUDITION_LINES = ["three",
                  "Can you count the orange fish?",
                  "Wow! A new friend is joining our tank!"]

DEFAULT_SETTINGS = {"speed": 0.95}  # VOICE.md: never sped up
# Per-section overrides, keyed by exact VOICE.md section heading.
# Numbers play rapid-fire as she taps, so keep them at full speed.
SECTION_SETTINGS = {
    "Numbers (counting taps)": {"speed": 1.0},
}

Job = namedtuple("Job", "text filename tight settings tone")

_ENGINE = None


def plan_jobs(voice_md=VOICE_MD, only=None):
    jobs = []
    for row in parse_voice_md(voice_md):
        if only is not None and row.filename[:-4] not in only:
            continue
        settings = {**DEFAULT_SETTINGS, **SECTION_SETTINGS.get(row.section, {})}
        jobs.append(Job(row.text, row.filename,
                        row.filename[:-4] in NUMBER_WORDS, settings, row.tone))
    return jobs


def ensure_model():
    MODEL_DIR.mkdir(parents=True, exist_ok=True)
    for name in MODEL_FILES:
        dst = MODEL_DIR / name
        if dst.exists():
            continue
        url = MODEL_BASE + name
        print(f"downloading {name} (one-time) ...")
        try:
            urllib.request.urlretrieve(url, dst)
        except OSError as e:
            dst.unlink(missing_ok=True)
            sys.exit(f"download failed ({e});\n"
                     f"fetch {url} manually into {MODEL_DIR}/ and rerun")


def engine():
    global _ENGINE
    if _ENGINE is None:
        try:
            from kokoro_onnx import Kokoro  # lazy: unit tests run without it
        except ImportError:
            sys.exit("kokoro-onnx not installed; run this script with uv:\n"
                     "  uv run tools/generate_voice.py ...")
        ensure_model()
        _ENGINE = Kokoro(str(MODEL_DIR / MODEL_FILES[0]),
                         str(MODEL_DIR / MODEL_FILES[1]))
    return _ENGINE


def resolve_voice(name):
    voices = sorted(engine().get_voices())
    if name not in voices:
        sys.exit(f"voice {name!r} not found; available: " + ", ".join(voices))
    return name


def synth(text, voice, settings):
    import soundfile as sf  # lazy: unit tests run without it
    samples, rate = engine().create(text, voice=voice,
                                    speed=settings["speed"], lang="en-us")
    buf = io.BytesIO()
    sf.write(buf, samples, rate, format="WAV")
    return buf.getvalue()


def postprocess(raw_wav_bytes, dst, tight):
    with tempfile.NamedTemporaryFile(suffix=".wav") as tmp:
        tmp.write(raw_wav_bytes)
        tmp.flush()
        subprocess.run(ffmpeg_args(tmp.name, dst, tight), check=True)


def cmd_audition(args):
    outdir = ROOT / "tools" / "audition"
    for name in AUDITION_VOICES:
        for text in AUDITION_LINES:
            dst = outdir / f"{name}-{text.split()[0].lower().strip('!')}.mp3"
            if args.dry_run:
                print(f"would synth {name}: {text!r} -> {dst.relative_to(ROOT)}")
                continue
            outdir.mkdir(exist_ok=True)
            resolve_voice(name)
            postprocess(synth(text, name, DEFAULT_SETTINGS), dst, tight=False)
            print(f"wrote {dst.relative_to(ROOT)}")
    if not args.dry_run:
        print("\nListen, pick a voice, then run: "
              "uv run tools/generate_voice.py batch --voice NAME")


def cmd_batch(args):
    only = set(args.only.split(",")) if args.only else None
    jobs = plan_jobs(only=only)
    if args.dry_run:
        for j in jobs:
            print(f"would synth [{'tight' if j.tight else 'padded'}] "
                  f"{j.filename}: {j.text!r}")
        print(f"{len(jobs)} clips planned")
        return
    voice = resolve_voice(args.voice)
    VOICE_DIR.mkdir(parents=True, exist_ok=True)
    for i, j in enumerate(jobs, 1):
        postprocess(synth(j.text, voice, j.settings), VOICE_DIR / j.filename, j.tight)
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
    if args.cmd == "batch" and not args.dry_run and not args.voice:
        sys.exit("batch needs --voice NAME (run audition first)")
    {"audition": cmd_audition, "batch": cmd_batch}[args.cmd](args)


if __name__ == "__main__":
    main()
```

- [ ] **Step 4: Run the full suite to verify it passes**

Run: `cd /Users/taylorernst/Code/fish-friends && python3 -m unittest discover -s tools/tests -t .`
Expected: PASS (23 tests).

- [ ] **Step 5: Smoke-test both dry-run paths under system Python (no deps needed)**

Run: `cd /Users/taylorernst/Code/fish-friends && python3 tools/generate_voice.py audition --dry-run && python3 tools/generate_voice.py batch --dry-run`
Expected: 18 "would synth" audition lines, then 108 "would synth" batch lines ending `108 clips planned`. No network, no import errors.

- [ ] **Step 6: Commit**

```bash
cd /Users/taylorernst/Code/fish-friends
git add tools/generate_voice.py tools/tests/test_generate_voice.py
git commit -m "feat: swap voice synthesis from ElevenLabs to local Kokoro"
```

---

### Task 3: Update docs and gitignore for the Kokoro workflow

**Files:**
- Modify: `README.md` (Status + "Finish the audio" sections)
- Modify: `.gitignore`

**Interfaces:**
- Consumes: the CLI from Task 2 (`uv run tools/generate_voice.py ...`).
- Produces: nothing code-facing; docs only.

- [ ] **Step 1: Update README.md**

Replace the two Status bullets about audio (the "NOT done yet" and "ElevenLabs call path" bullets) with:

```markdown
- NOT done yet: the 108 recorded voice lines. Until then the game
  speaks with the built-in robot voice (per-line fallback, by design).
- Voices are generated locally with Kokoro (free, offline, no API
  key). First run downloads ~340MB of model files into tools/models/.
```

Replace the "## Finish the audio (three commands)" section heading and its command block (keep the paragraph after it that starts "The batch writes all 108 MP3s...") with:

```markdown
## Finish the audio (two commands)

    uv run tools/generate_voice.py audition
    # listen to tools/audition/, pick a voice, then:
    uv run tools/generate_voice.py batch --voice af_heart
```

In that following paragraph, change `batch --voice NAME --only slug1,slug2` occurrences to stay as-is (still accurate), but check the paragraph for any remaining mention of ElevenLabs or API keys and remove it.

- [ ] **Step 2: Gitignore the model files**

Append to `.gitignore`:

```
tools/models/
```

- [ ] **Step 3: Verify no stale ElevenLabs references remain**

Run: `cd /Users/taylorernst/Code/fish-friends && grep -ri elevenlabs README.md tools/ docs/VOICE.md; echo "exit: $?"`
Expected: no matches (`exit: 1`).

- [ ] **Step 4: Commit**

```bash
cd /Users/taylorernst/Code/fish-friends
git add README.md .gitignore
git commit -m "docs: switch voice workflow docs to local Kokoro"
```

---

### Task 4: Live audition — generate the 18 sample clips

This task hits the real model (downloads ~340MB on first run, then ~a minute of CPU synthesis). It ends with a **user gate**: Taylor listens and picks a voice.

**Files:**
- Create: `tools/audition/*.mp3` (18 files, already gitignored)

**Interfaces:**
- Consumes: `uv run tools/generate_voice.py audition` from Task 2.
- Produces: 18 MP3s named `<voice>-<firstword>.mp3` (e.g. `af_heart-three.mp3`) for the user to audition.

- [ ] **Step 1: Run the audition**

Run: `cd /Users/taylorernst/Code/fish-friends && uv run tools/generate_voice.py audition`
Expected: model download messages on first run, then 18 `wrote tools/audition/...` lines, then the "Listen, pick a voice" hint. If a voice name errors, the message lists valid names — fix `AUDITION_VOICES` to match and rerun.

- [ ] **Step 2: Verify the output files are real audio**

Run: `cd /Users/taylorernst/Code/fish-friends && ls tools/audition/*.mp3 | wc -l && ffprobe -v error -show_entries format=duration -of csv=p=0 tools/audition/af_heart-three.mp3`
Expected: `18` and a duration between 0.4 and 3 seconds.

- [ ] **Step 3: USER GATE — Taylor listens and picks the voice**

Open the clips for Taylor (e.g. `open tools/audition/`) and stop. Do not proceed to Task 5 until Taylor names the winning voice. If none sound right, tune `DEFAULT_SETTINGS["speed"]` or swap `AUDITION_VOICES` entries and rerun Task 4 — it's free.

---

### Task 5: Full batch — generate all 108 clips and verify

Run only after Taylor picks a voice in Task 4. `VOICE_NAME` below is that pick.

**Files:**
- Create: `web/assets/voice/*.mp3` (108 files — these ship in the app, so they DO get committed)

**Interfaces:**
- Consumes: `uv run tools/generate_voice.py batch --voice VOICE_NAME` from Task 2; strict verifier runs automatically at the end.
- Produces: the shipped voice clips; a passing `verify_voice.py --strict`.

- [ ] **Step 1: Run the batch**

Run: `cd /Users/taylorernst/Code/fish-friends && uv run tools/generate_voice.py batch --voice VOICE_NAME`
Expected: 108 progress lines, then the verifier report, exit code 0. (~5-10 min of CPU synthesis.)

- [ ] **Step 2: Independently re-run the strict verifier**

Run: `cd /Users/taylorernst/Code/fish-friends && python3 tools/verify_voice.py --strict`
Expected: PASS — all VOICE.md lines, game-reachable lines, and on-disk files agree.

- [ ] **Step 3: USER GATE — review clips**

Open `tools/review.html` in a browser for Taylor to spot-check clips. Regenerate any rejects with `uv run tools/generate_voice.py batch --voice VOICE_NAME --only slug1,slug2`, then re-run the strict verifier.

- [ ] **Step 4: Commit the shipped audio**

```bash
cd /Users/taylorernst/Code/fish-friends
git add web/assets/voice
git commit -m "feat: add 108 Kokoro voice clips"
```

- [ ] **Step 5: Rebuild the app so the clips ship inside it**

Run: `cd /Users/taylorernst/Code/fish-friends/app && xcodegen generate` then build in Xcode / simulator per README. (This step is the existing README workflow, not new code; verify the game plays real clips instead of the robot voice.)
