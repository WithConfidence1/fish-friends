# Parent Settings, Reset Protections & Mixed Review — Design

Source inputs: `~/Downloads/handoff_settings_addition/` (README + two
mockups), Taylor's decisions of 2026-08-28, and the game source
`reference/Tap and Count.dc.html`. The handoff's §2 (addition round,
prompt strip, mature-tank state) is **already implemented** in the
game — it is verification material, not new work.

## Goals

1. A child-proof "Grown-up settings" overlay: level pin, round pacing,
   voice toggle, progress readout, and a protected
   clear-and-start-over.
2. Adaptive progression that no longer tops out: auto mode reaches
   levels 6–7 and then mixes review rounds instead of ending.
3. Progress that survives iOS storage purges (UserDefaults mirror).
4. A repeatable way to change game code at all: a build step that
   splices the readable reference source into the shipped bundle.

Out of scope: new voice lines (everything stays within the 108 clips),
child profiles, any change to round mechanics or art.

## 1. Build pipeline (prerequisite for everything else)

`web/index.html` is a design-canvas export: a loader plus the entire
readable game document embedded as ONE JSON-escaped string (the same
code as `reference/Tap and Count.dc.html`, with asset URLs remapped to
blob ids). Today's rule "never edit web/index.html" exists because
there was no build step. Now there is one:

- New `tools/build_web.py`: extracts the game's single `<script>`
  block from `reference/Tap and Count.dc.html`, JSON-escapes it, and
  splices it over the corresponding escaped script block inside
  `web/index.html`'s embedded source string. Nothing else in the
  bundle changes (loader, fonts, blob table untouched).
- Locating the splice region: find the escaped script block within the
  embedded string by its unescaped open/close markers
  (`<script` … `</script>` in escaped form); exactly one game
  script block exists in each file — the build fails loudly if the
  markers match zero or more than one region in either file.
- Idempotent: running it twice yields a byte-identical bundle.
- The dev rule becomes: **edit `reference/Tap and Count.dc.html`, run
  `python3 tools/build_web.py`, never hand-edit `web/index.html`.**
- Unit tests: marker-finding on the real files, idempotence,
  round-trip (after a build, the unescaped embedded script equals the
  reference script byte-for-byte).

## 2. Settings state & persistence

Settings move from React props (design-canvas harness) to
localStorage, with props kept as defaults for canvas preview:

- Key `tap-count-settings`, JSON `{level, pace, voice}`:
  `level`: `"auto"` or `1`–`7`; `pace`: `"natural"` | `"quick"`;
  `voice`: boolean.
- Defaults when key absent: `level "auto"`, `pace "natural"` (14s
  free-play before a round auto-starts — the shipped default changes
  from the prototype's 5s "quick demo"), `voice true`.
- Precedence: localStorage overrides props; props override built-in
  defaults. Reads go through one `settings()` accessor; `level()`,
  `voiceOn()`, `freeDur()` switch to it.
- `voice: false` silences **speech only** — both MP3 clips and the
  speechSynthesis fallback (the existing `voiceOn()` gate in `say()`
  already does exactly this). Blips, chords, and all other sound
  effects are unaffected.
- Level pin takes effect from the next round. While pinned, adaptive
  progression (`tap-count-progress`) is neither read for round
  selection nor written. Returning to `auto` resumes from the stored
  `{lvl, streak}` untouched by the pin.

## 3. The gate (child-proof, invisible)

Per handoff §1, with the corner moved to **top-left** (keeps the gate
away from Control Center's top-right swipe when the iPad isn't in
Guided Access; nothing in the game UI lives up there):

- iPad: one finger held in the top-left region (left 15% × top 15%)
  for 2 continuous seconds, stationary — lifting, or sliding out of
  the region, cancels. No visual affordance; normal taps there still
  ripple the water.
- Desktop/mouse: 3 clicks in that region within 1.5s.

## 4. Overlay UI

As specified in handoff §1 and `settings.png` (scrim, card styling,
Baloo 2, control order, "Done"), with these clarifications:

- Level dropdown options exactly: `auto (adaptive)`, `1 · count to 5`,
  `2 · count to 10`, `3 · add within 6`, `4 · add within 10`,
  `5 · take away (subtraction)`, `6 · pearl groups (multiplication)`,
  `7 · share the treats (division)`.
- Pacing dropdown: `Natural (rounds start after 14s)` / `Quick (5s)`.
- Voice checkbox labeled "Voice" (accent #F4711F), checked by default.
- Progress readout: "Progress: level {lvl} · {n} treasures collected"
  reading the stored progress (even while a pin is active).
- While the overlay is open the game pauses round auto-start (free
  play keeps animating behind the scrim; no new round begins).

## 5. Clear & undo (the protected reset)

Two-tap confirm per the handoff, hardened:

- Idle: grey `Clear treasures & progress`. First tap arms: red
  "Really clear everything? Tap again".
- **Armed state auto-disarms after 3 seconds** with no second tap
  (in addition to disarming on Done/close).
- Second tap while armed: first stash `{progress, treasures}` to
  `tap-count-backup`, then wipe `tap-count-treasures` and
  `tap-count-progress` (level 1, streak 0), live behind the overlay.
  Pets and backdrop reset automatically since they derive from
  treasure count. Settings (`tap-count-settings`) are NOT cleared.
- After a clear, the button becomes green-ish `Undo — bring it all
  back` for as long as the overlay stays open; tapping it restores
  both keys from `tap-count-backup`. Closing the overlay returns the
  button to idle, but `tap-count-backup` is retained until the next
  clear overwrites it (so a tearful discovery ten minutes later is
  still recoverable by a developer, if not by the UI).

## 6. Adaptive progression & mixed review

Current behavior (from the source): streak +1 on a clean round
(assists < 2) else −1; at +2 level up, at −2 level down;
**auto mode clamps `level()` to `min(5, lvl)`** so 6–7 are pin-only
and a mastered kid replays subtraction forever.

New behavior (auto mode only; pins behave as today):

- Remove the clamp: auto follows stored `lvl` across 1–7.
- **Review mix once she's in the top levels:** when stored `lvl` ≥ 6,
  each auto round is a coin flip — 50% a round of the current level's
  type, 50% a review round whose type is sampled uniformly from
  levels 1 to `lvl − 1`.
- **Mastery mode:** once `lvl` = 7 and streak reaches +2 (the level-up
  that has nowhere to go), the streak stays pinned there and every
  auto round samples uniformly from all seven level types. The tank
  never "ends".
- Review and mastery rounds never write `tap-count-progress` —
  only rounds of the current level's type move the streak, so a
  wobbly moment on an old skill can't demote her.

No new voice lines: every round type already has its full line set in
the shipped 108 clips.

## 7. UserDefaults mirror (shell)

localStorage in WKWebView can be purged by iOS under storage pressure
and dies with an app reinstall; the entire reward economy lives there.

- Game side: after any write to `tap-count-progress`,
  `tap-count-treasures`, `tap-count-settings`, or `tap-count-backup`,
  post the full four-key snapshot to
  `webkit.messageHandlers.persist.postMessage(...)` (guarded so the
  canvas/browser preview, which has no handler, is unaffected).
- Shell side (`GameWebView.swift`): a `WKScriptMessageHandler` for
  `persist` writes the snapshot into `UserDefaults` (key
  `gameState`). A `WKUserScript` injected at document start seeds
  localStorage from the saved snapshot **only for keys localStorage
  is missing** — so a purge restores from the mirror, and normal
  runs are untouched.

## 8. Handoff §2 (addition round) — verification only

The prompt strip, invite choreography, counting/celebration flow, and
mature-tank derivations described in the handoff exist in the source
(`drawPrompt`, `startRound`, treasure-derived pets/backdrops). The
implementation plan includes a verification pass against
`addition-mature-tank.png` (level-4 round in a 30+-treasure tank) but
no code changes unless a mismatch is found — any mismatch found gets
reported, not silently "fixed".

## 9. Testing & verification

- `tools/build_web.py` unit tests (see §1) join the existing suite;
  suite stays runnable on system Python with no new packages.
- Game-logic changes are verified in the browser (serve `web/` via
  local HTTP as in the original bring-up: gate via 3-click, settings
  persistence across reload, clear/undo, pinned levels 6–7) and in
  the iPad simulator (2s hold gate, a full round with voice, mirror
  round-trip: wipe localStorage via a relaunch after simulating a
  purge, confirm treasures come back).
- `python3 tools/verify_voice.py --strict` must still pass unchanged
  (no new lines).
- `voicelib.py`'s `slug()`/`game_lines()` need no changes; if any
  line text were touched (none should be), VOICE.md and the clips
  would have to move in lockstep.

## 10. Docs

README gains a short "Grown-up settings" paragraph for parents (how
to open the gate on iPad, what Clear does, that Undo exists while the
overlay is open) and the updated dev rule from §1.
