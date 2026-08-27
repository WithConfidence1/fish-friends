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
