"""App icon: the orange clownfish sprite centered on the game's
water gradient (#A9E4F6 to #2E93C4), flattened opaque, 1024x1024."""
import sys
from pathlib import Path

from PIL import Image

ROOT = Path(__file__).resolve().parents[1]
SIZE = 1024
TOP, BOTTOM = (0xA9, 0xE4, 0xF6), (0x2E, 0x93, 0xC4)


def lerp(a, b, t):
    return tuple(round(a[i] + (b[i] - a[i]) * t) for i in range(3))


def main():
    icon = Image.new("RGB", (SIZE, SIZE))
    px = icon.load()
    for y in range(SIZE):
        row = lerp(TOP, BOTTOM, y / (SIZE - 1))
        for x in range(SIZE):
            px[x, y] = row

    fish = Image.open(ROOT / "web" / "assets" / "kit" / "fish-orange.png").convert("RGBA")
    target_w = int(SIZE * 0.72)
    fish = fish.resize((target_w, int(fish.height * target_w / fish.width)),
                       Image.LANCZOS)
    icon.paste(fish, ((SIZE - fish.width) // 2, (SIZE - fish.height) // 2), fish)

    out = (ROOT / "app" / "Resources" / "Assets.xcassets"
           / "AppIcon.appiconset" / "icon-1024.png")
    icon.save(out, "PNG")
    print(f"wrote {out}")


if __name__ == "__main__":
    main()
