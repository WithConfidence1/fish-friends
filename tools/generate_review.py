"""Emit tools/review.html: every clip with a play button, its line,
section, and tone, plus a reject list Taylor can copy into
generate_voice.py batch --only ... for regeneration."""
import html
import sys
from pathlib import Path

if __package__ in (None, ""):
    sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from tools.voicelib import parse_voice_md

ROOT = Path(__file__).resolve().parents[1]

HEAD = """<!DOCTYPE html><html><head><meta charset="utf-8">
<title>Fish Friends voice review</title>
<style>
body{font-family:-apple-system,sans-serif;margin:2rem;max-width:60rem}
h2{margin:1.6rem 0 .2rem}.tone{color:#666;font-style:italic;margin:0 0 .6rem}
.row{display:flex;align-items:center;gap:.7rem;padding:.25rem 0;border-bottom:1px solid #eee}
.row.missing .line{color:#b00}.line{flex:1}audio{height:2rem}
#rejects{width:100%;height:4rem;margin-top:1rem}
</style></head><body>
<h1>Voice review: 108 clips</h1>
<p>Play everything. Tick the box on any clip that misses
"warm, unhurried, small smile". Red rows are missing files.</p>
"""

TAIL = """<h2>Rejects</h2>
<textarea id="rejects" readonly placeholder="tick boxes above"></textarea>
<p>Regenerate with: <code>python3 tools/generate_voice.py batch --voice NAME
--only &lt;paste list&gt;</code></p>
<script>
document.querySelectorAll('audio').forEach(a=>a.addEventListener('error',
  ()=>a.closest('.row').classList.add('missing')));
const out=document.getElementById('rejects');
document.querySelectorAll('input[type=checkbox]').forEach(c=>
  c.addEventListener('change',()=>{
    out.value=[...document.querySelectorAll('input:checked')]
      .map(c=>c.dataset.slug).join(',');
  }));
</script></body></html>
"""


def main():
    rows = parse_voice_md(ROOT / "docs" / "VOICE.md")
    parts, section = [HEAD], None
    for r in rows:
        if r.section != section:
            section = r.section
            parts.append(f"<h2>{html.escape(section)}</h2>"
                         f"<p class=tone>{html.escape(r.tone)}</p>")
        slug = r.filename[:-4]
        parts.append(
            f'<div class=row><input type=checkbox data-slug="{slug}">'
            f'<audio controls preload=none src="../web/assets/voice/{r.filename}"></audio>'
            f'<span class=line>{html.escape(r.text)}</span>'
            f'<code>{r.filename}</code></div>')
    parts.append(TAIL)
    out = ROOT / "tools" / "review.html"
    out.write_text("\n".join(parts), encoding="utf-8")
    print(f"wrote {out} ({len(rows)} rows)")


if __name__ == "__main__":
    main()
