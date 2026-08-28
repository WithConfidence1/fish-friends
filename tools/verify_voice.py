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
    if len(rows) != 151:
        problems.append(f"VOICE.md parsed to {len(rows)} rows, expected 151")

    for row in rows:
        if slug(row.text) + ".mp3" != row.filename:
            problems.append(f"VOICE.md mismatch: slug({row.text!r}) != {row.filename}")

    voice_slugs = {r.filename[:-4] for r in rows}
    game_slugs = {slug(t) for t in game_lines()}
    for s in sorted(game_slugs - voice_slugs):
        problems.append(f"game line has no VOICE.md row (that line will be silent): {s}")
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
