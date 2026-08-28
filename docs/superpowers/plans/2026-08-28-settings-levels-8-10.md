# Parent Settings, Levels 8–10 & Mixed Review Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Implement the spec at `docs/superpowers/specs/2026-08-28-parent-settings-mixed-review-design.md`: a build step for the game bundle, grown-up settings overlay with protected reset, silent missing-clip audio, three new levels (count to 20 / tap until / make ten) with 43 new af_bella clips, mixed-review adaptive progression, and a UserDefaults mirror in the iPad shell.

**Architecture:** Game logic lives in the single `<script>` block of `reference/Tap and Count.dc.html` (a canvas-rendered component; DOM is one wrap div + canvas). A new `tools/build_web.py` splices that script into the shipped bundle `web/index.html`, where the whole source document is embedded as one JSON-escaped string. Voice stays pre-recorded: VOICE.md ⇄ `voicelib.game_lines()` ⇄ MP3s, gated by `verify_voice.py --strict`. The Swift shell gains a message handler that mirrors localStorage to UserDefaults.

**Tech Stack:** Vanilla JS on canvas (no framework code in our changes), Python 3 stdlib tools + unittest, kokoro-onnx via `uv run tools/generate_voice.py`, SwiftUI/WebKit shell, XcodeGen.

## Global Constraints

- Unit tests run under system Python 3.14, no new packages: `python3 -m unittest discover -s tools/tests -t .` from the repo root.
- After Task 1 lands: game changes are made ONLY in `reference/Tap and Count.dc.html`, then `python3 tools/build_web.py` regenerates `web/index.html`. Never hand-edit `web/index.html`.
- Voice: new clips are af_bella only, generated with `uv run tools/generate_voice.py batch --voice af_bella --only <slugs>`; existing clips are never regenerated. `python3 tools/verify_voice.py --strict` must pass at the end of the voice tasks and at the end of the plan.
- Missing clip = silence. No speechSynthesis anywhere in the game after Task 4.
- Settings key `tap-count-settings` = `{"level": "auto"|1..10, "pace": "natural"|"quick", "voice": true|false}`; defaults auto / natural (14s) / true. localStorage overrides props; props override defaults.
- Exact voice line text in Task 2 is canonical — the game (Task 6) must emit byte-identical strings.
- Browser verification serves the repo's `web/` directory over local HTTP (e.g. `python3 -m http.server 8123 -d web`) and drives `http://localhost:8123/index.html`.

---

### Task 1: `tools/build_web.py` — splice game source into the bundle

**Files:**
- Create: `tools/build_web.py`
- Test: `tools/tests/test_build_web.py`

**Interfaces:**
- Consumes: `reference/Tap and Count.dc.html` (source of truth), `web/index.html` (bundle).
- Produces: CLI `python3 tools/build_web.py` (rewrites `web/index.html` in place; `--check` exits 1 if the bundle is stale without writing). Library functions `extract_script(html_text) -> str` and `splice(bundle_text, script_text) -> str` used by tests and later tasks.

Background for the implementer: the bundle embeds the ENTIRE reference document as one JSON string (inside a `"..."` literal on the bundle's loader line; `\n` escapes, `</script>` for closing tags, asset URLs remapped to opaque ids). The game script block appears inside that embedded string with its `<script type="text/x-dc" ... >` open tag and `</script>` close tag intact. Only the script *body* differs between reference and bundle-embedded copies (the reference body is the same code; the embedded copy is its JSON-escaped form). The splice must therefore: find the escaped body between the escaped open/close markers, and replace it with `json.dumps(new_body)[1:-1]` (JSON-escape without the surrounding quotes) — plus the same `</` → `</` protection the bundle uses (apply `.replace('</', '<\\u002F')` after json-escaping and verify the round-trip).

- [ ] **Step 1: Write failing tests**

```python
import json
import unittest
from pathlib import Path

from tools.build_web import extract_script, splice, REFERENCE, BUNDLE

ROOT = Path(__file__).resolve().parents[2]


class TestBuildWeb(unittest.TestCase):
    def test_extract_finds_single_game_script(self):
        body = extract_script(REFERENCE.read_text(encoding="utf-8"))
        self.assertIn("class Component extends DCLogic", body)
        self.assertIn("startRound()", body)

    def test_bundle_embeds_reference_script(self):
        # After a build, unescaping the bundle's embedded body yields the
        # reference body byte-for-byte.
        ref_body = extract_script(REFERENCE.read_text(encoding="utf-8"))
        bundle = BUNDLE.read_text(encoding="utf-8")
        built = splice(bundle, ref_body)
        embedded = extract_embedded_body(built)  # helper in build_web
        self.assertEqual(json.loads('"%s"' % embedded), ref_body)

    def test_splice_is_idempotent(self):
        ref_body = extract_script(REFERENCE.read_text(encoding="utf-8"))
        bundle = BUNDLE.read_text(encoding="utf-8")
        once = splice(bundle, ref_body)
        self.assertEqual(once, splice(once, ref_body))

    def test_splice_rejects_ambiguous_markers(self):
        with self.assertRaises(SystemExit):
            splice("no markers here", "x = 1")
```

(Adjust the import list to what you actually name — `extract_embedded_body` must be exported for the test. The marker for locating the embedded body: the escaped open tag contains `text/x-dc` and `data-dc-script`; the close marker is the FIRST `</script>` after it. Exactly one occurrence in the bundle, or `sys.exit` with a message.)

- [ ] **Step 2: Run tests, verify they fail** (`python3 -m unittest tools.tests.test_build_web -v` → import error)

- [ ] **Step 3: Implement `tools/build_web.py`** — stdlib only (`json`, `re`, `sys`, `argparse`, `pathlib`). `REFERENCE = ROOT / "reference" / "Tap and Count.dc.html"`, `BUNDLE = ROOT / "web" / "index.html"`. `extract_script`: the block starting at `<script type="text/x-dc"` through its matching `</script>`; body = text after the open tag's `>` up to the close tag; error if zero or >1 matches. `main()`: read both, splice, write only if changed, print `built` or `unchanged`; `--check` prints `stale`/`clean` and exits accordingly.

- [ ] **Step 4: Run the full suite** — all pass; then run `python3 tools/build_web.py` and confirm it prints `unchanged` (reference and bundle currently agree), and `git status --porcelain` shows no diff.

- [ ] **Step 5: Commit** — `feat: build step splicing game source into the web bundle`

---

### Task 2: Voice enumeration — VOICE.md + `voicelib` for levels 8–10

**Files:**
- Modify: `docs/VOICE.md` (three new sections; preamble fallback sentence)
- Modify: `tools/voicelib.py` (`NUMBER_WORDS`, `game_lines()`, docstring)
- Test: `tools/tests/test_voicelib.py`, `tools/tests/test_generate_voice.py`

**Interfaces:**
- Consumes: existing `parse_voice_md`, `slug`, `game_lines`.
- Produces: `NUMBER_WORDS` = one…twenty (20 entries). `game_lines()` additionally returns every line below. VOICE.md gains exactly **43** rows. Task 3 generates exactly these 43 slugs; Task 6 must emit these exact strings.

**The canonical 43 new lines** (filenames are `slug(text) + ".mp3"`):

1. Numbers (tight, section "Numbers (counting taps)" gains ten rows): `eleven`, `twelve`, `thirteen`, `fourteen`, `fifteen`, `sixteen`, `seventeen`, `eighteen`, `nineteen`, `twenty`.
2. New section `## Count to 20 celebrations` (*Bright, proud.*), ten rows, n = 11..20: `{word}! {n} orange fish! Hooray!` (e.g. `eleven! 11 orange fish! Hooray!` → `eleven-11-orange-fish-hooray.mp3`).
3. New section `## Tap until (missing addend)` (*Playful challenge.*), five + six rows:
   - `Can you make it {word(T)}? Tap the new fish!` for T = 5..9.
   - The six addition-celebration pairs not already in VOICE.md: `eight! two and six makes 8! Hooray!`, `eight! six and two makes 8! Hooray!`, `nine! two and seven makes 9! Hooray!`, `nine! seven and two makes 9! Hooray!`, `nine! three and six makes 9! Hooray!`, `nine! six and three makes 9! Hooray!`.
4. New section `## Make ten (number bonds)` (*Wonder, gentle challenge.*), twelve rows:
   - `Look! {word(A)} pearls.` for A = 3..8 (six rows).
   - `Tap the clams until we have ten!` (one row).
   - The five bond celebrations not already present: `ten! three and seven makes 10! Hooray!`, `ten! four and six makes 10! Hooray!`, `ten! six and four makes 10! Hooray!`, `ten! seven and three makes 10! Hooray!`, `ten! eight and two makes 10! Hooray!` (5+5 already exists).

**`game_lines()` additions** (W = NUMBER_WORDS, now 20 long; `lines = set(W)` at the top already absorbs the new numbers):

```python
    for n in range(11, 21):  # L8 count to 20
        lines.add(f"{W[n - 1]}! {n} orange fish! Hooray!")
    for t in range(5, 10):   # L9 tap until: T 5..9, A 2..T-2, B = T-A
        lines.add(f"Can you make it {W[t - 1]}? Tap the new fish!")
        for a in range(2, t - 1):
            b = t - a
            lines.add(f"{W[t - 1]}! {W[a - 1]} and {W[b - 1]} makes {t}! Hooray!")
    for a in range(3, 9):    # L10 make ten: A 3..8, B = 10-A
        b = 10 - a
        lines.add(f"Look! {W[a - 1]} pearls.")
        lines.add(f"ten! {W[a - 1]} and {W[b - 1]} makes 10! Hooray!")
    lines.add("Tap the clams until we have ten!")
```

Also update the `game_lines` docstring (L8 count N 11..20; L9 until T 5..9, A 2..T-2; L10 bond A 3..8) and VOICE.md's preamble: replace the "only falls back to the browser voice for missing files" sentence with "a missing file means that line is simply silent" (keep the gradual-adoption sentence intact otherwise).

- [ ] **Step 1: Write/adjust failing tests.** In `test_generate_voice.py`: change `test_plans_all_108_clips` to expect **151** and rename it `test_plans_all_151_clips`. In `test_voicelib.py`: update any count assertions (run the suite to see which fail); add:

```python
    def test_new_level_lines_enumerated(self):
        lines = game_lines()
        self.assertIn("twenty", lines)
        self.assertIn("eleven! 11 orange fish! Hooray!", lines)
        self.assertIn("Can you make it nine? Tap the new fish!", lines)
        self.assertIn("nine! seven and two makes 9! Hooray!", lines)
        self.assertIn("Look! three pearls.", lines)
        self.assertIn("ten! eight and two makes 10! Hooray!", lines)
        self.assertIn("Tap the clams until we have ten!", lines)

    def test_number_words_reach_twenty(self):
        self.assertEqual(len(NUMBER_WORDS), 20)
        self.assertEqual(NUMBER_WORDS[10], "eleven")
        self.assertEqual(NUMBER_WORDS[19], "twenty")
```

- [ ] **Step 2: Run tests, verify the new/changed ones fail.**
- [ ] **Step 3: Implement** — extend `NUMBER_WORDS` (`"eleven", "twelve", "thirteen", "fourteen", "fifteen", "sixteen", "seventeen", "eighteen", "nineteen", "twenty"`), add the `game_lines()` block above, write the VOICE.md rows (exact text/slug per the canonical list; keep the existing table format `| text | `file.mp3` |`), fix the preamble sentence.
- [ ] **Step 4: Full suite passes.** Then run `python3 tools/verify_voice.py` (non-strict) — it must report the 43 new files as missing-but-pending and NO text mismatches. If it reports a mismatch between VOICE.md and game_lines, fix the text — do not suppress.
- [ ] **Step 5: Commit** — `feat: enumerate voice lines for levels 8-10 (43 new clips)`

---

### Task 3: Generate the 43 new clips (operational)

**Files:** Create: 43 MP3s in `web/assets/voice/` (committed).

**Interfaces:** Consumes Task 2's VOICE.md and the existing generator; models already in `tools/models/`.

- [ ] **Step 1:** Compute the slug list (from VOICE.md rows added in Task 2; `python3 -c` one-liner using `parse_voice_md` minus files on disk is fine) and run `uv run tools/generate_voice.py batch --voice af_bella --only <comma-separated-43-slugs>`.
- [ ] **Step 2:** `python3 tools/verify_voice.py --strict` → must pass (151 files). Spot-check with ffprobe that `eleven.mp3` is < 1s (tight) and one sentence clip is 1–4s.
- [ ] **Step 3:** Commit ONLY the new MP3s — `feat: add 43 af_bella clips for levels 8-10`

---

### Task 4: Game core — settings from localStorage, silent voice, persist hook

**Files:**
- Modify: `reference/Tap and Count.dc.html` (script block only), then run `python3 tools/build_web.py`
- Modify: the `data-props` attribute's `level` options list (add `8 · count to 20`, `9 · tap until (missing addend)`, `10 · make ten (number bonds)` — it is `&quot;`-escaped HTML; follow the existing pattern)

**Interfaces (source anchors from the current file):**
- `progress()` line ~43, `level()` ~46, `voiceOn()` ~47, `freeDur()` ~48, speech code `pickVoice`/`tts`/`say` ~107–140, `componentWillUnmount` ~40, progress write in `finishRound()` ~257–263, treasures write ~385.
- Produces for later tasks: `settings()` accessor, `saveSettings(patch)`, `persist()`, and `say()` that is clip-or-silent. Task 5 builds the overlay on these; Task 7 consumes the `persist` message format `{progress, treasures, settings, backup}` (each the raw JSON string from localStorage, or null).

- [ ] **Step 1: Implement in the reference script:**

```js
  settings() {
    if (!this._settings) {
      let s = {};
      try { s = JSON.parse(localStorage.getItem('tap-count-settings') || '{}'); } catch (e) {}
      const propLevel = String(this.props.level || 'auto');
      const propPace = String(this.props.pace || 'natural');
      this._settings = {
        level: s.level != null ? s.level : (propLevel.match(/^(\d+)/) ? +propLevel.match(/^(\d+)/)[1] : 'auto'),
        pace: s.pace || (propPace.startsWith('quick') ? 'quick' : 'natural'),
        voice: s.voice != null ? s.voice : this.props.voice !== false,
      };
    }
    return this._settings;
  }
  saveSettings(patch) {
    Object.assign(this.settings(), patch);
    try { localStorage.setItem('tap-count-settings', JSON.stringify(this._settings)); } catch (e) {}
    this.persist();
  }
  persist() {
    try {
      if (window.webkit && webkit.messageHandlers && webkit.messageHandlers.persist) {
        const g = k => { try { return localStorage.getItem(k); } catch (e) { return null; } };
        webkit.messageHandlers.persist.postMessage({
          progress: g('tap-count-progress'), treasures: g('tap-count-treasures'),
          settings: g('tap-count-settings'), backup: g('tap-count-backup') });
      }
    } catch (e) {}
  }
```

Rewire: `level()` → `const l = this.settings().level; return l === 'auto' ? Math.max(1, Math.min(10, this.progress().lvl)) : l;` — **note the props default pace changes to natural and the regex to `\d+`**. Keep the auto clamp at 10 (Task 6 adds the rounds; until then the ladder cannot exceed 7 anyway because `finishRound` caps `lvl < 7` — leave that cap for Task 6). `voiceOn()` → `return this.settings().voice;`. `freeDur()` → `return this.settings().pace === 'quick' ? 5 : 14;`.

Silent voice: delete `pickVoice()` and `tts()` entirely; in `say()`, drop the `_noClip`/tts paths — play the clip, and on `.play()` rejection or missing file do nothing; delete both `speechSynthesis.cancel()` calls (in `say` and `componentWillUnmount`). Update the comment at ~line 129 to `// recorded clips only; a missing clip means the line is silent`.

Add `this.persist()` immediately after the two existing `localStorage.setItem` writes (progress in `finishRound`, treasures in the reward tick).

- [ ] **Step 2: Build and verify in the browser.** `python3 tools/build_web.py` (prints `built`). Serve `web/` on :8123. In the browser: game loads, a count round runs with clip audio; `localStorage.setItem('tap-count-settings','{"level":2}')` + reload → rounds are always count-to-10 (pin works); `'{"voice":false}'` → next round has blips but no speech; with voice on, rounds auto-start ~14s after free play begins (natural default). Confirm `speechSynthesis` no longer appears in the built bundle (`grep -c speechSynthesis web/index.html` → 0 within the game body; the loader itself never contained it).
- [ ] **Step 3: Full Python suite still passes; `verify_voice.py --strict` still passes** (line text untouched).
- [ ] **Step 4: Commit** — `feat: settings from localStorage, silent missing clips, persist hook`

---

### Task 5: Gate + grown-up settings overlay + protected clear/undo

**Files:** Modify: `reference/Tap and Count.dc.html`, rebuild bundle.

**Interfaces:**
- Consumes: `settings()`, `saveSettings()`, `persist()`, `progress()`, `this.treasures`, `this.wrap` (the fixed wrap div — append DOM overlay to it), `tap(e)` (pointerdown entry, ~line 292), `boot()` (add listeners).
- Produces: `this.settingsOpen` flag — while true, `tick()` must not auto-start rounds (guard the `phase === 'free' && this.pt > this.freeDur()` line by resetting `this.pt = 0` when `settingsOpen`).

Behavior (spec §3–§5): gate = pointer held ≥2s inside x<0.15∧y<0.15 of the wrap, stationary (cancel if pointerup, pointercancel, or movement out of the region; track via `pointerdown` in `tap()` + `pointerup`/`pointermove`/`pointercancel` listeners added in `boot()`); OR 3 pointerdowns in that region within 1.5s. Overlay = DOM `<div>` appended to `this.wrap` (scrim rgba(8,40,56,0.55); card #F7FBFD radius 22px padding 28px 30px width min(420px,88vw) font 'Baloo 2' color #14333D): header "Grown-up settings" (22px/800) + Done pill (#E2EEF3); Level `<select>` with `auto (adaptive)` + the ten labels from the spec §4 list; Pacing `<select>` (`Natural (rounds start after 14s)` / `Quick (5s)`); Voice `<input type=checkbox>` (accent-color #F4711F); divider; progress line "Progress: level {stored lvl} · {treasures.length} treasures collected" (13px #5A7683); Clear button. Selects/checkbox write through `saveSettings` immediately. Done removes the overlay, disarms Clear, sets `settingsOpen=false`.

Clear button states: idle (grey #7A97A5, "Clear treasures & progress") → armed on tap (red #D6452B, "Really clear everything? Tap again", auto-disarm after 3s via timeout) → on second tap: write `tap-count-backup` = JSON `{progress: <current progress JSON>, treasures: <current treasures JSON>}`, then remove both keys, reset in-memory state live (`this._prog = {lvl:1,streak:0}`; `this.treasures = []`; `this.petCount = 0`; remove pet fish (`this.fish = this.fish.filter(f => f.color !== 'pet')`); `this.bgIdx = 0`), `persist()`, and switch the button to the undo state (green #3E8E5A, "Undo — bring it all back"). Undo tap: restore both keys from backup, rebuild in-memory state the same way boot does (re-slot treasures with `tSlot`, re-add pets, `bgIdxFor`), `persist()`, button returns to idle. Closing the overlay resets the button to idle but leaves `tap-count-backup` in storage.

- [ ] **Step 1: Implement** (gate tracking + `openSettings()`/`closeSettings()` building the DOM imperatively; keep it one focused method group; no framework).
- [ ] **Step 2: Build; browser verification** on :8123 — mouse path: 3 quick clicks top-left → overlay opens; level pin from dropdown changes next round; pacing quick → ~5s auto-start; voice off → silent speech; progress line correct; Clear arms, auto-disarms after 3s of no tap; Clear→confirm wipes tank live (treasures gone behind scrim, `localStorage` keys removed, backup present); Undo restores everything; Done closes; while overlay open no round auto-starts. Also verify a plain click in the corner still ripples water and that a 4th rapid click doesn't re-open after Done.
- [ ] **Step 3: Python suite + strict verifier still green. Commit** — `feat: grown-up settings overlay with protected clear and undo`

---

### Task 6: Levels 8–10 rounds + mixed-review progression

**Files:** Modify: `reference/Tap and Count.dc.html`, rebuild bundle.

**Interfaces (anchors):** `words` array ~144, `slots()` ~146, `startRound()` ~166, `finishRound()` ~254, invite-duration map in `tick()` ~362, assist hint in `tick()` ~368, `tap()` targets branch ~318, `drawPrompt()` ~657, `drawMulDiv()` ~585. Voice strings MUST byte-match Task 2's canonical list.

**6a. Plumbing.** Extend `words` with eleven…twenty. In `finishRound()`: change the ladder cap `pr.lvl < 7` → `pr.lvl < 10`; skip the whole progress-update block when `this.isReview` is true OR level is pinned (current guard `String(this.props.level||'auto').startsWith('auto')` becomes `this.settings().level === 'auto' && !this.isReview`). Mastery: when `pr.lvl === 10 && pr.streak >= 2`, hold `pr.streak = 2` instead of levelling.

**6b. Round selection with review mix.** At the top of `startRound()`:

```js
    const stored = Math.max(1, Math.min(10, this.progress().lvl));
    const pinned = this.settings().level !== 'auto';
    let lvl = pinned ? this.settings().level : stored;
    this.isReview = false;
    if (!pinned && stored >= 6) {
      const mastered = stored === 10 && this.progress().streak >= 2;
      if (mastered) { lvl = 1 + Math.floor(Math.random() * 10); this.isReview = lvl !== stored; }
      else if (Math.random() < 0.5) { lvl = 1 + Math.floor(Math.random() * (stored - 1)); this.isReview = true; }
    }
```

(`level()` stays as Task 4 wrote it for display/pin purposes; `startRound` uses this local `lvl` in place of the old `const lvl = this.level()`.)

**6c. Level 8 — count to 20.** `lvl === 8`: `roundType = 'count'`, `roundN = 11 + Math.floor(Math.random() * 10)`. Extend `slots()`'s multi-row branch: for `n > 10` use three rows (`Math.ceil(n/3)` / `Math.ceil((n-top)/2)` / remainder at y0 0.20/0.35/0.50, same spacing formula, sp cap 0.11) so 20 fish fit; the existing `isTarget` width cap (slotPitch × 1.45, ≤27% H) already shrinks sprites. Celebration/count voice work unchanged (`words` now reaches twenty; the count celebration template at ~line 277 already produces `eleven! 11 orange fish! Hooray!`). Number-bubble font already shrinks for num > 9.

**6d. Level 9 — tap until.** `lvl === 9`: `roundType = 'until'`; `this.T = 5 + Math.floor(Math.random() * 5)` (5..9); `A = 2 + Math.floor(Math.random() * (this.T - 3))` (2..T−2); `B = T − A`; `roundN = T`. Setup mirrors the add branch: want = roundN orange fish; slots via `slots(roundN, true, A)`; fish `i < A` gather to the left arc; fish `i >= A` become mode `'wait'` — parked at the right margin (`x = 0.97 + (i-A)*0.05`, y spread 0.25..0.55, dimmed 0.45 like backed fish, gently bobbing), each holding its target slot in `gx/gy`. `targets = ` the waiting fish ONLY. Invite says (700ms) existing `'Look! ' + words[A-1] + ' orange fish are here.'` then (3300ms) `'Can you make it ' + words[T-1] + '? Tap the new fish!'`. Invite duration map: `until: 5.6`. Tap handling: reuse the targets branch — tapping a waiting fish sets `mode='gather'`, and the count voice line must announce the RUNNING TOTAL `A + counted` (in the targets branch, for `roundType === 'until'` say `words[A + this.counted - 1]` after increment, and set `best.num = A + this.counted` so the bubble shows the running total; re-taps re-say `words[best.num-1]` which is already total-correct). Finish when `counted >= B` (guard: for `'until'`, the finish check is `this.counted >= this.B`). `finishRound` for `'until'` says `words[T-1] + '! ' + words[A-1] + ' and ' + words[B-1] + ' makes ' + T + '! Hooray!'` (the shared addition template — pairs guaranteed present by Task 2). Assist machinery: `targets.find(x => !x.num)` works as-is; the level-2 hint reuses the existing orange-fish hint (extend the ternary: `'until'` → same line as default). Prompt strip: in the add/sub branch of `drawPrompt`, treat `'until'` like add with `showN = T`, `split = A`, and alpha `i < A ? 1 : (i - A) < this.counted ? 1 : 0.35`. Numerals appear only above group-B fish as they arrive, showing the running total: draw for `i >= A && (i - A) < this.counted` with value `i + 1` (the fish at absolute index A reads A+1, and the last reads T).
**6e. Level 10 — make ten.** `lvl === 10`: `roundType = 'bond'`; `A = 3 + Math.floor(Math.random() * 6)` (3..8); `B = 10 − A`; `roundN = 10`; `this.T = 10`. Reuse the pearl machinery: `this.pearls` = A open pearls arranged like the mul arc (single row centered near y 0.56, spacing 0.055–0.07) each `num: 0` but pre-counted visually solid; `this.clams` = B closed clams parked near the sand right of center (`x` spread 0.62..0.9, `y = sandU−0.05` region), drawn with `im['clam-pink']`/`im['clam-purple']` alternating, width ~64·fsc. `targets = this.clams` (each `{x, y, num:0, bounce:0, wig:0, w:64}`). Orange fish are cleared to the margins like mul (`want = 0` path). Invite (700ms) `'Look! ' + words[A-1] + ' pearls.'`, (3300ms) `'Tap the clams until we have ten!'`; invite duration `bond: 5.2`. Tapping a clam: it "opens" — mark `num = A + this.counted` (after increment), bounce, burst, and push a new pearl into the pearl row (`this.pearls.push({...})` at the next slot) so the row grows toward ten; say `words[A + this.counted - 1]` (running total). Finish when `counted >= B`: `finishRound` for `'bond'` says `'ten! ' + words[A-1] + ' and ' + words[B-1] + ' makes 10! Hooray!'`. Hint (assist level 2): `'Can you tap another pearl?'` (existing clip; extend the hint ternary for `'bond'`). Drawing: extend `drawMulDiv` to render `this.clams` (closed clam image, gold glow + numeral bubble once `num` set, same style as pearls) — pearls themselves render via the existing pearl loop. Prompt strip for `'bond'`: pearl-dot style like mul but a single group of ten dots: first A solid at full alpha from the start, the rest fill as `counted` grows (`k < A + this.counted ? 1 : 0.5`).

**6f. Data-props preview parity** is already handled (Task 4 added the three option labels).

- [ ] **Step 1: Implement 6a–6e** in the reference script; run `python3 tools/build_web.py`.
- [ ] **Step 2: Browser verification** on :8123, using localStorage pins and a helper to force rounds (`localStorage.setItem('tap-count-settings','{"level":8}')` etc., reload each time):
  - L8: a 11–20 fish round; every fish fits on screen; count to the end; hear teen-number clips; celebration line plays; no overlap disasters (screenshot).
  - L9: A fish gather left, dimmed fish wait right; prompt shows A solid + hollow to T with a `+`; tapping waiting fish announces running totals (A+1…T); celebration correct; re-tap repeats the total; idle 12s produces the fish hint.
  - L10: A pearls appear, clams wait; tapping clams grows the pearl row and counts A+1…10; celebration `ten! … makes 10! Hooray!`; hint after idle is the pearl line.
  - Review mix: set `tap-count-progress` to `{"lvl":7,"streak":0}`, settings auto; reload several times/rounds and confirm both level-7 rounds and lower-level rounds occur, and that `tap-count-progress` only changes after rounds of the type matching lvl 7 (watch the key in devtools across rounds).
  - Mastery: set `{"lvl":10,"streak":2}` → rounds sample all types; progress stays `{"lvl":10,"streak":2}`.
- [ ] **Step 3: Python suite + `verify_voice.py --strict` still pass** (they will catch any line-text drift between game and VOICE.md via the shared enumeration — but the true check is Task 2's canonical list; grep the reference for each new template to confirm byte-match).
- [ ] **Step 4: Commit** — `feat: levels 8-10 (count to 20, tap until, make ten) with mixed review`

---

### Task 7: Shell mirror — UserDefaults persistence

**Files:** Modify: `app/Sources/GameWebView.swift`

**Interfaces:** Consumes the `persist` message from Task 4: `{progress, treasures, settings, backup}` (string-or-null values). Produces UserDefaults key `gameState` = `[String: String]` of the non-null pairs, and a seed script restoring them.

- [ ] **Step 1: Implement.** In `makeUIView`: add `config.userContentController`; register the coordinator as `WKScriptMessageHandler` for name `"persist"`; extend `Coordinator` with `userContentController(_:didReceive:)` that casts `message.body` to `[String: Any]`, keeps `String` values for the four keys, and writes the dict to `UserDefaults.standard` under `"gameState"`. Before creating the web view, build the seed script from the saved dict:

```swift
        if let saved = UserDefaults.standard.dictionary(forKey: "gameState") as? [String: String] {
            let names = ["progress": "tap-count-progress", "treasures": "tap-count-treasures",
                         "settings": "tap-count-settings", "backup": "tap-count-backup"]
            let js = saved.compactMap { key, value -> String? in
                guard let store = names[key],
                      let data = try? JSONSerialization.data(withJSONObject: value, options: .fragmentsAllowed),
                      let literal = String(data: data, encoding: .utf8) else { return nil }
                return "if (localStorage.getItem('\(store)') === null) localStorage.setItem('\(store)', \(literal));"
            }.joined(separator: "\n")
            config.userContentController.addUserScript(
                WKUserScript(source: js, injectionTime: .atDocumentStart, forMainFrameOnly: true))
        }
```

- [ ] **Step 2: Build check** — `cd app && xcodegen generate` then a simulator build (headless) must succeed with zero errors.
- [ ] **Step 3: Simulator verification** (after Task 8's rebuild is also fine, but do a first pass now): launch, play one round to completion, then `xcrun simctl spawn booted defaults read <bundle-id> gameState` (bundle id from `app/project.yml`) shows the four keys with JSON strings. A true storage-purge simulation is impractical headlessly; do NOT attempt to delete WKWebsiteDataStore internals. Acceptable evidence for the seed path: (a) `defaults read` shows the mirror updating after play, (b) the seed script only writes keys localStorage lacks (verified by reading the code), (c) the game demonstrably reads those keys at boot (browser evidence from Tasks 4–6). Note this limitation in the report.
- [ ] **Step 4: Commit** — `feat: mirror game state to UserDefaults with boot-time seed`

---

### Task 8: Docs, final build, end-to-end simulator verification

**Files:** Modify: `README.md`; rebuild bundle + app.

- [ ] **Step 1: README.** Add a `## Grown-up settings` section: hold a finger in the TOP-LEFT corner for 2 seconds (3 quick clicks on desktop) to open; level pin / pacing / voice toggle; Clear requires two taps and offers Undo while the panel is open; the game is silent for any missing voice line (no robot voice). Update the Development section's rule: "Game changes go in `reference/Tap and Count.dc.html`; run `python3 tools/build_web.py` to regenerate `web/index.html`; never edit `web/index.html` by hand." Update the Status date and clip count (151 clips, af_bella).
- [ ] **Step 2: Full gates:** `python3 -m unittest discover -s tools/tests -t .`, `python3 tools/verify_voice.py --strict`, `python3 tools/build_web.py --check` (clean), `cd app && xcodegen generate` + simulator build.
- [ ] **Step 3: Simulator end-to-end:** install + launch; verify with taps/screenshots: a normal round with voice; open the gate with a 2s top-left touch (control tool: `touch_path` with a single point held — use points [{x:60,y:60,dt_ms:0},{x:60,y:60,dt_ms:2200}]); pin level 9, play a tap-until round to celebration; pin level 10, make-ten round; pin level 4 and compare the addition round against the handoff mockup `~/Downloads/handoff_settings_addition/addition-mature-tank.png` (spec §8 — report any mismatch, don't fix); back to auto; Clear + Undo; Done. Confirm `defaults read` mirror updated. Screenshots into `docs/verification/2026-08-28/`.
- [ ] **Step 4: Commit** — `docs: grown-up settings runbook; verification evidence`
