# Fish Friends

Cartoon aquarium math game for the iPad, wrapped as a native app.
The game itself is the bundled HTML prototype in `web/`; the Swift
shell in `app/` just gives it full screen, offline, wake lock, and
audio through the mute switch.

## Status (2026-08-27)

- Built and verified in the iPad Simulator: shell, icon, full game
  loop (count round, number bubbles, celebration, treasure, relaunch).
  Evidence in `docs/verification/2026-08-27/`.
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
