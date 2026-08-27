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
