"""Write the ikat (endek-inspired) ribbon partial used above the sign-in and sign-up forms (DESIGN.md)."""

from pathlib import Path

OUTPUT = Path(__file__).resolve().parent.parent / "src" / "templates" / "partials" / "ikat.html"

rects = []
for y in range(6):
    for x in range(24):
        d = abs(((x + 6) % 12) - 6) + abs(y - 2.5)
        edge = 1 if (x * 7 + y * 13) % 5 == 0 else 0
        o = 1 if d + edge < 4.5 else 0.45 if d + edge < 5.5 else 0.1
        rects.append(f'<rect x="{x}" y="{y}" width="1" height="1" opacity="{o}"/>')
svg = (
    '<svg viewBox="0 0 24 6" preserveAspectRatio="none" shape-rendering="crispEdges" '
    'fill="currentColor" aria-hidden="true" class="block h-[132px] w-full text-accent">'
    + "".join(rects)
    + "</svg>"
)
OUTPUT.parent.mkdir(parents=True, exist_ok=True)
OUTPUT.write_text(svg + "\n", encoding="utf-8")
print(f"Wrote {OUTPUT}")
