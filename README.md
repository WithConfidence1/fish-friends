# Fish Friends

Cartoon aquarium math game for the iPad, wrapped as a native app.
The game itself is the bundled HTML prototype in `web/`; the Swift
shell in `app/` just gives it full screen, offline, wake lock, and
audio through the mute switch.

## Status (2026-08-28)

- Built and verified in the iPad Simulator: shell, icon, full game
  loop (count round, number bubbles, celebration, treasure, relaunch),
  levels 8-10, and Grown-up settings end to end. Evidence in
  `docs/verification/2026-08-27/` and `docs/verification/2026-08-28/`.
- The 151 voice clips are generated with Kokoro (voice `af_bella`) and
  committed. Remaining work: spot-check clips in `tools/review.html`
  (regenerate rejects with `batch --voice af_bella --only slug1,slug2`).
- Voices are generated locally with Kokoro (free, offline, no API
  key). First run downloads ~340MB of model files into tools/models/.
  A missing clip is silent, never a robot/fallback voice (see
  Grown-up settings below).

## Finish the audio (two commands)

    uv run tools/generate_voice.py audition
    # listen to tools/audition/, pick a voice, then:
    uv run tools/generate_voice.py batch --voice af_bella

The batch writes all 151 MP3s into `web/assets/voice/`, post-processes
them with ffmpeg (numbers tight, sentences padded 0.2s), and runs the
strict verifier. Review every clip in `tools/review.html` (open it in
a browser); tick rejects and regenerate just those with
`batch --voice NAME --only slug1,slug2`. Rebuild the app afterward so
the clips ship inside it. To re-record a line yourself later,
overwrite its MP3 in `web/assets/voice/` and rebuild. Nothing else
changes.

## Grown-up settings

Hold a finger in the top-left corner of the screen for 2 continuous
seconds (3 quick clicks in the same corner on desktop) to open a
hidden settings panel. There's no visible affordance — normal taps in
that corner still behave as ordinary water taps.

The panel lets you pin a specific level (or leave it on
`auto (adaptive)`), set round pacing (natural vs. quick), and toggle
voice on/off. A level pin takes effect on the next round; adaptive
progression pauses while pinned. Below that is a progress readout and
**Clear treasures & progress**, which needs two taps to confirm
(tapping again within a few seconds wipes everything) and offers
**Undo** to restore the wiped state while the panel stays open. Tap
**Done** to close.

The game never substitutes a robot or fallback voice: any voice line
missing from `web/assets/voice/` is simply skipped, so she stays
silent for that one line.

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
- Game changes go in `reference/Tap and Count.dc.html`; run
  `python3 tools/build_web.py` to regenerate `web/index.html`; never
  edit `web/index.html` by hand.
