# Handoff: Fish Friends — Tap and Count (iPad early-math aquarium)

## Overview
A cartoon aquarium game for a 4-year-old on iPad. The aquarium itself is the math interface — fish, pearls, and treats act as physical manipulatives. No quiz UI, no worksheets, no reading, no timers, no failure states. The child thinks she is playing with an aquarium; underneath she is building number sense (counting → cardinality → addition → subtraction → equal groups → fair sharing).

Target platform: native iPad app (SwiftUI + SpriteKit recommended, or the developer's choice). Always-landscape-friendly, works at any aspect; portrait acceptable.

## About the Design Files
The files in this bundle are **design references created in HTML** — a fully working prototype showing intended look, behavior, timing, and audio. They are NOT production code to copy directly. The task is to **recreate this design as a native iPad app** using appropriate frameworks (SpriteKit/SwiftUI or similar). `Tap and Count.dc.html` contains the complete reference implementation: every rule, timing constant, animation, and line of dialogue is in its single script block. `Fish Friends - iPad.html` is a self-contained bundled build for quick play-testing in Safari.

## Fidelity
**High-fidelity.** The prototype is the intended product: sprites, layout proportions, choreography, dialogue, and reward pacing should be recreated faithfully. Positions are proportional (0–1 of canvas width/height), not fixed pixels.

## The One Screen
A single full-screen aquarium. No menus, no HUD, no settings visible to the child.

Visual stack (back to front):
1. Water: vertical gradient #A9E4F6 → #5FBFE3 (45%) → #2E93C4
2. Unlocked backdrop image (see Rewards), cover-fit, cross-fades in over ~3s
3. Animated light rays (4 white beams, 10% opacity, slow sway)
4. Background fish (non-target fish, dimmed to 45% alpha during challenges)
5. Sand: #F2DC96 wavy band, top edge at 85% of height; darker strip #D6B26A at 50% below
6. Plants anchored to sand: kelp clusters (assets weed-a/b/d, heights ~110–165px, sway ±0.04rad), corals (coral-blue, coral-pink)
7. Sand dwellers: starfish ×2, crab (patrols x 8–60%, pauses randomly), treasure chest at x 86%, treasure collection, hermit crab pet
8. Mid-water: jellyfish ×2 (pulse-propelled: bell contraction pushes upward), pets (seahorse, puffer, ray)
9. Turtle (the guide): rests at x 10%, y 68% during free play; swims to x 13%, y 64% to run a challenge
10. Target fish (orange clownfish) during challenges: full alpha, drawn on top, white glow if uncounted, gold glow + number bubble once counted
11. Prompt strip at top of water (see Challenges), particles (stars/hearts/bubbles), ambient bubbles

## Core loop / state machine
Phases: `free → invite → count → celebrate → reward → free`

- **free**: everything swims naturally. Tapping any fish = wiggle + bounce + bubble puff + blip sound. Tapping a jelly = squish. Tapping empty water = tiny bubbles. Tapping the TURTLE starts a challenge immediately; otherwise one auto-starts after 5s ("quick demo" pacing) or 14s ("natural" — ship default).
- **invite**: turtle swims in, speaks the challenge line(s). Orange fish choreograph (see per-level). Non-target fish dim to 45% and drift to the edges — still moving, never frozen. Duration: 2.6s (counting) up to 7.4s (subtraction).
- **count**: child taps targets. Each first tap: fish hops (squash-and-stretch), sparkle burst, rising two-tone blip (pitch climbs with count), voice says the number, a white number bubble (orange text, Baloo 2 font) sticks above the fish. Re-tapping a counted fish: re-bounce + repeats its number — NEVER double-counts. Tapping a non-target fish: it darts away shyly, low blip — no penalty, no error state. Tap targets are generous: ≥76px radius.
- **celebrate**: on final count (0.8s delay). Voice states the full math fact. Fish fly staggered loop-de-loops, star/heart particle bursts, 4-note chord (C5-E5-G5-C6 triangles), starfish hop. ~3s (longer for multiplication — see skip counting).
- **reward**: a treasure drifts down from the surface to the collection (see Rewards), then everything returns to free play. Turtle returns to rest spot.

### Gentle help (during count)
- 5s idle: next uncounted target wiggles, emits bubbles, white pulsing ellipse ring beneath it
- 12s idle: voice hint ("Can you find another orange fish? Tap it!" — level-specific lines in VOICE.md)
- 20s idle: cycle back to the wiggle. Never escalates beyond this; never solves it for her.
- Using level-2 help twice in a round marks the round "assisted" for the difficulty ladder.

## Levels (adaptive ladder, invisible)
Stored progress: level 1–7 + streak. Two clean rounds (no heavy help) → level up; two assisted rounds → level down. Never announced.

1. **Count to 5**: N = 2–5 orange fish gather into a loose arc (still bobbing, tail-beating — alive, not frozen). "Can you count the orange fish?"
2. **Count to 10**: N = 6–10, two rows.
3. **Addition within 6**: A (1–3) fish gather left; B (1–3) more swim in from the right edge ~3s later, gather right. "Look! Three orange fish are here." → "Two more are coming! How many fish altogether?" Child counts ALL (counting-all strategy).
4. **Addition within 10**: same, A,B = 2–5.
5. **Subtraction (take away)**: A = 4–8 fish gather; after settling, B of them (answer ≥ 2) turn and visibly swim off-screen with bubble trails. "Oh! Three are swimming away. How many are left?" Child counts survivors.
6. **Multiplication (pearl groups)**: A = 2–3 shells on the sand, each with B = 2–3 pearls above it. "Look! Three shells. Every shell has two pearls!" → "How many pearls altogether? Tap them all!" Child counts every pearl. Celebration models skip counting: each shell's pearls bounce together as voice counts "two… four… six!" (1.1s apart), then the fact line.
7. **Division (share the treats)**: N = A×B treats float at the surface; A = 2–3 hungry orange fish line up. "Six yummy treats! Can you share them with the three hungry fish?" Child taps a fish → treat arcs down to it, collects beneath it. FAIRNESS RULE: a fish that is ahead of the minimum refuses — wiggles, low blip, and (≤ once per 4s) says "I have enough for now! My friend is hungry too!" Round completes when the pile is empty; everyone has B. "Six treats shared with three fish… two each! Fair sharing, hooray!"

### Prompt strip (pictorial equation, no reading)
Centered near the top of the water during invite/count. Mini orange-fish icons fill in (30%→100% alpha) as she counts, tiny numbers above counted ones.
- Addition: [A fish] + [B fish], orange "+" glyph
- Subtraction: [A−B fish] − [B fish]; the take-away group lights up when those fish leave; departed school members fade to 28%
- Multiplication: pearl dots clustered by group
- Division: one mini fish per sharer, treats fill beneath each

## Rewards (the dopamine ladder)
- **Every completed round**: one treasure drifts down beside the chest and stays FOREVER (persisted). Pool of 13, cycled: shell, gem-purple, star-big, coin, clam-pink, heart, gem-blue, pearl-orb, starfish-pink, gem-pink, star-gold, clam-purple, gem-teal. Collection arranged in rows of 9 near the chest (x 58.5–96%), capped at 40 (oldest rotate out).
- **Every 5th treasure**: a creature permanently joins the tank: seahorse → pufferfish → ray → hermit crab. Turtle: "Wow! A new friend is joining our tank!" + chord; the pet swims in from the edge. Pets keep habitats: seahorse mid-water (y 35–65%), puffer upper (20–55%), ray glides low (55–72%), hermit crawls the sand.
- **10 / 20 / 30 treasures**: the backdrop transforms (bg-reef → bg-wreck → bg-cave), cross-fade ~3s, "Wow! Look! Our whole tank is changing!"

## Audio
- **Voice**: ALL 108 lines are enumerated in VOICE.md with exact filenames. The app should play recorded MP3s (assets/voice/<slug>.mp3); the prototype falls back to speech synthesis when a clip is missing. Number words one–ten are the most-heard clips.
- **SFX** (synthesized in prototype; may ship as baked samples): count blip = triangle wave, 440+80·n Hz rising ~220 Hz over 0.18s (pitch climbs with the count); tap wiggle = sine 500→820 Hz 0.12s; shy dart = 300→200 Hz; celebration chord = C5/E5/G5/C6 triangles staggered 120ms; treasure fall = 880→1320 Hz 0.4s.
- iOS: audio unlocked on first touch.

## Animation notes (feel)
- Fish swim with tail-beat surge: speed multiplied by (1 + 0.45·sin(phase)) — push then glide; gentle body rock ±0.05rad and vertical bob.
- Direction changes turn smoothly: horizontal scale eases through a thin middle (min 15% width) rather than instant mirroring.
- Tap bounce: anticipation squash → 38px hop with stretch → soft landing; volume preserved (sx ·= 2 − sy).
- Celebration loop-de-loop: fish fly a full vertical circle (r ≈ 46px) with matching rotation, staggered 0.22s apart.
- Jellyfish: bell pump scales width up/height down ~10%, propulsion tied to pump.
- All motion is frame-rate independent (dt-based). devicePixelRatio capped at 2.

## State & persistence
- `treasures`: array of {img} (positions derived from index) — persists
- `progress`: {lvl: 1–7, streak: int} — persists
- Pets and backdrop are DERIVED from treasures.length (no extra state)
- Screen wake lock held while playing. Prototype also has parent-facing tweaks (pin level, pacing, voice on/off) — in the app these belong in a hidden parent gate, never child-visible.

## Design tokens
- Fonts: Baloo 2 (800 for numbers, 600 body). Numbers in bubbles: white circle, 4px #FF8A3C border, #F4711F text.
- Water: #A9E4F6 / #5FBFE3 / #2E93C4 · Sand: #F2DC96, shadow #D6B26A · Number/prompt accent: #F4711F
- Creature scale: target fish ~128px base (auto-shrinks to fit formation: ≤ 1.45× slot pitch, ≤ 27% of height), background fish 56–86px, turtle 150px, minimum tap radius 76px.

## Assets (all in assets/kit/, transparent PNGs)
Cropped from the owner's licensed sprite sheet (uploads/pasted-1787667202295-0.png in the source project): fish-orange, fish-blue/yellow/pink/purple/green, turtle, jelly-blue, jelly-pink, crab*, starfish*, starfish-pink*, seaweed weed-a/b/d, coral-blue, coral-pink, shell, chest, star-gold, heart, star-big, gems ×4, coin, pearl-orb, clam-pink, clam-purple, seahorse, puffer, ray, hermit, bg-reef, bg-wreck, bg-cave, bubble-speech (unused in final design).
(*) crab and both starfish were repainted at 4× resolution (256–300px) to survive retina scaling — style-match reference for any future sprite upgrades. The originals are ≤160px; a higher-res re-export of the full sheet would improve everything.

## Out of scope / not yet built (clean list)
1. Voice recordings — script ready in VOICE.md; app should ship with real clips, not TTS
2. Chest anticipation (fills/rattles as rounds complete, bursts at 5) — designed, not implemented
3. Affectionate pets (nuzzle fingertip, heart bubble on tap) — designed, not implemented
4. Celebration variety (rotate: conga line, bubble storm, octopus applause, treasure rain)
5. Child's name in celebration lines (needs name-specific clips)
6. Parent gate + progress peek (level, streak)
7. Counting-on addition variant (first group pre-counted) as a level between 4 and 5
8. Subitizing flash moments ("how many jellyfish swam past?!")

## Files
- `Tap and Count.dc.html` — reference implementation (single file; all logic in one script block)
- `Fish Friends - iPad.html` — bundled standalone build for Safari play-testing
- `VOICE.md` — all 108 spoken lines with filenames and tone direction
- `assets/kit/` — all sprites
