"""Draw the three read-eval-print loops of "The idea" as SVG.

Usage:
    python3 tool/make-repl-loops.py <lucide.ttf> index.html
        puts the wide and the tall layout into index.html, between the comments
        <!-- repl-loops:begin --> and <!-- repl-loops:end -->
    python3 tool/make-repl-loops.py <lucide.ttf> <name>.svg
        writes the wide layout to <name>.svg and the tall one to <name>-tall.svg

The icons are glyphs of the Lucide font (ISC licence) that ProjecturEd uses:
asset/font/lucide.ttf of projectured-julia. Text and icons take the colors of
the page (--ink, --ink-soft, --ink-faint, --sans), so the picture follows the
light and the dark theme. The page shows the wide layout, and the tall one on a
narrow screen.
"""
import math
import re
import sys

from fontTools.pens.boundsPen import BoundsPen
from fontTools.pens.svgPathPen import SVGPathPen
from fontTools.ttLib import TTFont

R = 150            # radius of a loop
NODE = 52          # radius of the disc behind a step icon
BAND = 16          # width of an arrow band
HEAD = 30          # length of the head of a band
ANGLE = {"Read": 90, "Eval": -30, "Print": -150}
LOOPS = [
    ("human", ("Human", "Loop"), {"Read": ["eye"], "Eval": ["face-slightly-smiling"], "Print": ["pointer"]}),
    ("editor", ("Editor", "Loop"), {"Read": ["keyboard", "mouse"], "Eval": ["settings"], "Print": ["monitor"]}),
    ("ai", ("AI Assistant", "Loop"), {"Read": ["scan-text"], "Eval": ["bot"], "Print": ["square-terminal"]}),
]
LINKS = ("user interaction", "tool calls")
CONVERSATION = "conversation"

# the loops side by side
WIDE_CENTERS = [(230, 250), (750, 250), (1270, 250)]
WIDE_VIEW = (40, -66, 1420, 492)
# the loops one above the other, for a narrow screen
TALL_CENTERS = [(250, 232), (250, 690), (250, 1148)]
TALL_VIEW = (48, 10, 544, 1318)

STYLE = """
  .repl-loops { --loop-human: #5b82ff; --loop-editor: #36ad80; --loop-ai: #e3a236; }
  .repl-loops text { font-family: var(--sans, system-ui, -apple-system, "Segoe UI", sans-serif); text-anchor: middle; fill: var(--ink, #15181d); }
  .repl-loops .loop-title { font-size: 28px; font-weight: 700; }
  .repl-loops .stage { font-size: 19px; font-weight: 700; }
  .repl-loops .link-label { font-size: 18px; font-weight: 600; fill: var(--ink-soft, #545b66); }
  .repl-loops--tall .loop-title { font-size: 31px; }
  .repl-loops--tall .stage { font-size: 22px; }
  .repl-loops--tall .link-label { font-size: 21px; text-anchor: start; }
  .repl-loops .icon { fill: var(--ink, #15181d); }
  .repl-loops .band { fill: none; stroke-width: 16; }
  .repl-loops .band.human { stroke: var(--loop-human); }  .repl-loops .band-head.human { fill: var(--loop-human); }
  .repl-loops .band.editor { stroke: var(--loop-editor); } .repl-loops .band-head.editor { fill: var(--loop-editor); }
  .repl-loops .band.ai { stroke: var(--loop-ai); }        .repl-loops .band-head.ai { fill: var(--loop-ai); }
  .repl-loops .node.human { fill: var(--loop-human); fill-opacity: .18; }
  .repl-loops .node.editor { fill: var(--loop-editor); fill-opacity: .18; }
  .repl-loops .node.ai { fill: var(--loop-ai); fill-opacity: .22; }
  .repl-loops .sync { fill: none; stroke: var(--ink-faint, #8a919c); stroke-width: 5; }
  .repl-loops .sync-head { fill: var(--ink-faint, #8a919c); }
  .repl-loops .conversation { fill: none; stroke: var(--ink-faint, #8a919c); stroke-width: 4; stroke-dasharray: 12 10; stroke-linecap: round; }
"""
DESCRIPTION = (
    "Three separate read-eval-print loops: the human, the editor and the AI assistant. "
    "The human reads with the eyes, decides, and acts with the hand. The editor reads the keyboard and the mouse, "
    "evaluates, and prints to the screen. The AI assistant reads text, the model decides, and it prints a tool call. "
    "The human and the editor meet at the user interaction; the editor and the AI assistant meet at the tool calls. "
    "A dashed arc joins the human and the AI assistant: the conversation.")


def make_icon(glyphs, name, cx, cy, size):
    """The glyph `name`, centered on (cx, cy), with its larger side equal to `size`."""
    path = SVGPathPen(glyphs)
    glyphs[name].draw(path)
    # The box that the font stores for a glyph starts at (0, 0), so measure the outline itself.
    bounds = BoundsPen(glyphs)
    glyphs[name].draw(bounds)
    x_min, y_min, x_max, y_max = bounds.bounds
    width, height = x_max - x_min, y_max - y_min
    scale = size / max(width, height)
    tx = cx - scale * (x_min + width / 2)
    ty = cy + scale * (y_min + height / 2)
    return (f'<path class="icon" transform="translate({tx:.2f} {ty:.2f}) scale({scale:.5f} {-scale:.5f})" '
            f'd="{path.getCommands()}"/>')


def get_point(center, theta, radius=R):
    t = math.radians(theta)
    return (center[0] + radius * math.cos(t), center[1] - radius * math.sin(t))


def make_head(tip, direction, length, half_width, cls):
    """A triangle with its tip at `tip`, pointing along the unit vector `direction`."""
    (x, y), (dx, dy) = tip, direction
    bx, by = x - dx * length, y - dy * length
    return (f'<path class="{cls}" d="M{x:.1f} {y:.1f} L{bx - dy * half_width:.1f} {by + dx * half_width:.1f} '
            f'L{bx + dy * half_width:.1f} {by - dx * half_width:.1f} z"/>')


def make_band(center, start, end, loop):
    """A clockwise band on a loop from angle `start` down to angle `end`, which ends in a wide head."""
    t = math.radians(end)
    direction = (math.sin(t), math.cos(t))
    x0, y0 = get_point(center, start)
    xs, ys = get_point(center, end + math.degrees(HEAD * 0.8 / R))
    return (f'<path class="band {loop}" d="M{x0:.1f} {y0:.1f} A{R} {R} 0 0 1 {xs:.1f} {ys:.1f}"/>'
            + make_head(get_point(center, end), direction, HEAD, BAND * 1.25, f"band-head {loop}"))


def make_sync(start, end):
    """A two-way arrow between two loops, from `start` to `end`."""
    (x0, y0), (x1, y1) = start, end
    length = math.hypot(x1 - x0, y1 - y0)
    dx, dy = (x1 - x0) / length, (y1 - y0) / length
    h = 16
    return (f'<path class="sync" d="M{x0 + dx * h * 0.8:.1f} {y0 + dy * h * 0.8:.1f} '
            f'L{x1 - dx * h * 0.8:.1f} {y1 - dy * h * 0.8:.1f}"/>'
            + make_head(start, (-dx, -dy), h, 9, "sync-head") + make_head(end, (dx, dy), h, 9, "sync-head"))


def make_conversation(start, control_start, control_end, end):
    """A dashed two-way arc from the loop of the human to the loop of the assistant."""
    heads = []
    for tip, control in ((start, control_start), (end, control_end)):
        dx, dy = tip[0] - control[0], tip[1] - control[1]
        n = math.hypot(dx, dy)
        heads.append(make_head(tip, (dx / n, dy / n), 16, 9, "sync-head"))
    # the dashed line stops short of each tip, so the dash does not show through the head
    s0 = (start[0] + (control_start[0] - start[0]) * 0.1, start[1] + (control_start[1] - start[1]) * 0.1)
    s1 = (end[0] + (control_end[0] - end[0]) * 0.1, end[1] + (control_end[1] - end[1]) * 0.1)
    return (f'<path class="conversation" d="M{s0[0]:.1f} {s0[1]:.1f} C{control_start[0]:.1f} {control_start[1]:.1f} '
            f'{control_end[0]:.1f} {control_end[1]:.1f} {s1[0]:.1f} {s1[1]:.1f}"/>' + "".join(heads))


def make_text(x, y, content, cls, rotate=None):
    turn = f' transform="rotate({rotate} {x:.1f} {y:.1f})"' if rotate is not None else ""
    return f'<text x="{x:.1f}" y="{y:.1f}" class="{cls}"{turn}>{content}</text>'


def make_loops(glyphs, centers):
    gap = math.degrees((NODE + 12) / R)
    parts = []
    for center, (loop, title, steps) in zip(centers, LOOPS):
        cx, cy = center
        parts.append(make_band(center, ANGLE["Read"] - gap, ANGLE["Eval"] + gap, loop))
        parts.append(make_band(center, ANGLE["Eval"] - gap, ANGLE["Print"] + gap, loop))
        parts.append(make_band(center, ANGLE["Print"] - gap + 360, ANGLE["Read"] + gap, loop))
        for stage, theta in ANGLE.items():
            x, y = get_point(center, theta)
            parts.append(f'<circle class="node {loop}" cx="{x:.1f}" cy="{y:.1f}" r="{NODE}"/>')
            names = steps[stage]
            if len(names) == 1:
                parts.append(make_icon(glyphs, names[0], x, y, 46))
            else:
                # a keyboard and a small mouse, centered together
                parts.append(make_icon(glyphs, names[0], x - 13, y, 42))
                parts.append(make_icon(glyphs, names[1], x + 25, y + 4, 24))
            parts.append(make_text(x, y + NODE + 26, stage, "stage"))
        parts.append(make_text(cx, cy + 8, title[0], "loop-title"))
        parts.append(make_text(cx, cy + 42, title[1], "loop-title"))
    return parts


def make_wide(glyphs):
    centers = WIDE_CENTERS
    parts = make_loops(glyphs, centers)
    reach = R * math.cos(math.radians(30)) + NODE + 14
    y = centers[0][1] + 20
    for (a, _), (b, _), label in zip(centers, centers[1:], LINKS):
        parts.append(make_sync((a + reach, y), (b - reach, y)))
        parts.append(make_text((a + b) / 2, y - 22, label, "link-label"))
    (hx, hy), (ax, _) = centers[0], centers[-1]
    start, end = (hx + 108, hy - 170), (ax - 108, hy - 170)
    parts.append(make_conversation(start, (start[0] + 100, start[1] - 150), (end[0] - 100, end[1] - 150), end))
    parts.append(make_text((start[0] + end[0]) / 2, start[1] - 112 - 14, CONVERSATION, "link-label"))
    return parts


def make_tall(glyphs):
    centers = TALL_CENTERS
    parts = make_loops(glyphs, centers)
    for (x, a), (_, b), label in zip(centers, centers[1:], LINKS):
        top, bottom = a + R + 26, b - R - NODE - 14
        parts.append(make_sync((x, top), (x, bottom)))
        parts.append(make_text(x + 18, (top + bottom) / 2 + 7, label, "link-label"))
    (hx, hy), (_, ay) = centers[0], centers[-1]
    start, end = get_point(centers[0], 12, R + 46), get_point(centers[-1], 12, R + 46)
    parts.append(make_conversation(start, (start[0] + 120, start[1] + 200), (end[0] + 120, end[1] - 200), end))
    middle_x = start[0] + 120 * 0.75 + 16
    parts.append(make_text(middle_x, (hy + ay) / 2, CONVERSATION, "link-label", rotate=90))
    return parts


def make_svg(parts, view, layout):
    x, y, w, h = view
    title_id = f"repl-loops-{layout}-title"
    return (f'<svg class="repl-loops repl-loops--{layout}" viewBox="{x} {y} {w} {h}" role="img" '
            f'aria-labelledby="{title_id}" xmlns="http://www.w3.org/2000/svg">\n'
            f'<title id="{title_id}">{DESCRIPTION}</title>\n<style>{STYLE}</style>\n'
            + "\n".join(parts) + "\n</svg>")


def put_into_page(page_path, wide, tall):
    page = open(page_path).read()
    pattern = re.compile(r"(<!-- repl-loops:begin -->\n).*?(\s*<!-- repl-loops:end -->)", re.S)
    if not pattern.search(page):
        sys.exit(f"{page_path} has no <!-- repl-loops:begin --> ... <!-- repl-loops:end --> block")
    notice = "<!-- The icons are Lucide glyphs (https://lucide.dev), under the ISC and the MIT licence: assets/Lucide-ISC.txt -->\n"
    page = pattern.sub(lambda m: m.group(1) + notice + wide + "\n" + tall + m.group(2), page, count=1)
    open(page_path, "w").write(page)


if __name__ == "__main__":
    font_path, target = sys.argv[1], sys.argv[2]
    glyphs = TTFont(font_path).getGlyphSet()
    wide = make_svg(make_wide(glyphs), WIDE_VIEW, "wide")
    tall = make_svg(make_tall(glyphs), TALL_VIEW, "tall")
    if target.endswith(".html"):
        put_into_page(target, wide, tall)
    else:
        open(target, "w").write(wide + "\n")
        open(target[:-len(".svg")] + "-tall.svg", "w").write(tall + "\n")
