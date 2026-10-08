"""Generate placeholder SVG pictures for every point option in scene.json.

Run: backend/venv/Scripts/python.exe scripts/generate_placeholder_images.py [--force]

These are simple colored cards with the option label written on them, meant to
be swapped for real pictograms (ARASAAC or book pictograms) later.
"""

import argparse
import json
import colorsys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
SCENE_PATH = ROOT / "frontend" / "public" / "scene" / "scene.json"
IMAGES_DIR = ROOT / "frontend" / "public" / "scene" / "images"

SVG_TEMPLATE = """<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 200 200" width="200" height="200">
  <rect width="200" height="200" rx="16" fill="{bg}" />
  <text x="100" y="108" font-family="sans-serif" font-size="{font_size}" font-weight="600"
        text-anchor="middle" fill="{fg}">{label}</text>
</svg>
"""


def color_for(index: int, total: int) -> tuple[str, str]:
    hue = (index / max(total, 1)) % 1.0
    r, g, b = colorsys.hsv_to_rgb(hue, 0.45, 0.92)
    bg = f"#{int(r*255):02x}{int(g*255):02x}{int(b*255):02x}"
    return bg, "#222222"


def wrap_label(label: str) -> str:
    words = label.split()
    if len(words) <= 1:
        return f"<tspan x='100' dy='0'>{label}</tspan>"
    mid = (len(words) + 1) // 2
    line1 = " ".join(words[:mid])
    line2 = " ".join(words[mid:])
    return (
        f"<tspan x='100' dy='-12'>{line1}</tspan>"
        f"<tspan x='100' dy='24'>{line2}</tspan>"
    )


def collect_options(scene: dict) -> dict[str, str]:
    options: dict[str, str] = {}
    for turn in scene["turns"]:
        for opt in turn["point"]["options"]:
            options[opt["id"]] = opt["label"]
    return options


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--force", action="store_true")
    args = parser.parse_args()

    scene = json.loads(SCENE_PATH.read_text(encoding="utf-8"))
    options = collect_options(scene)
    IMAGES_DIR.mkdir(parents=True, exist_ok=True)

    created, skipped = [], []
    for idx, (opt_id, label) in enumerate(sorted(options.items())):
        path = IMAGES_DIR / f"{opt_id}.svg"
        if path.exists() and not args.force:
            skipped.append(path)
            continue
        bg, fg = color_for(idx, len(options))
        font_size = 20 if len(label) <= 10 else 16
        svg = SVG_TEMPLATE.format(bg=bg, fg=fg, label=wrap_label(label), font_size=font_size)
        path.write_text(svg, encoding="utf-8")
        created.append(path)

    print(f"Created {len(created)} image(s):")
    for p in created:
        print(f"  {p.relative_to(ROOT)}")
    print(f"Skipped {len(skipped)} image(s) that already existed:")
    for p in skipped:
        print(f"  {p.relative_to(ROOT)}")


if __name__ == "__main__":
    main()
