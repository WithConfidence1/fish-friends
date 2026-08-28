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
