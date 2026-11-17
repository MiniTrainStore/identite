#!/usr/bin/env python3
"""Compose the MiniTrainStore logo from the traced locomotive and Montserrat.

The locomotive (ressources/logo/locomotive.svg) was traced once from the
original 1050 px PNG. Text is set with the real Montserrat outlines (shaped
with HarfBuzz, so kerning is kept) and placed against the locomotive's
geometry: the two lines share the italic axis and the same width, and keep
a constant clearance from the nose and the swoosh.

    uv run scripts/build_logo.py

Needs Montserrat ExtraBold Italic and SemiBold Italic (Debian/Ubuntu:
fonts-montserrat), found with fc-match.
"""
from __future__ import annotations

import io
import math
from pathlib import Path
import re
import subprocess

import cairosvg
from fontTools.pens.svgPathPen import SVGPathPen
from fontTools.pens.transformPen import TransformPen
from fontTools.ttLib import TTFont
from PIL import Image
import uharfbuzz as hb

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "ressources" / "logo"
NAVY, SKY, WHITE = "#133a57", "#31aadf", "#ffffff"

# Layout, in locomotive units (the traced artwork is 1050 x 213).
BLOCK_CENTRE = 94     # vertical centre of the text block (train body: 0 to ~172)
LINE_GAP = 17         # main baseline -> top of the tagline's tallest glyph
TAG_TRACKING = 45     # tagline letter-spacing, in font units
TAG_RATIO = .55       # tagline size relative to the main line
TEXT_LEFT = 496       # left edge of the main line at its baseline
TEXT_RIGHT = 1032     # right edge of the main line


def font_path(style: str) -> str:
    result = subprocess.run(
        ["fc-match", "-f", "%{file}", f"Montserrat:style={style}"],
        check=True, capture_output=True, text=True,
    )
    if "Montserrat" not in result.stdout:
        raise SystemExit(f"Montserrat {style} not installed")
    return result.stdout


class Line:
    """One line of text, shaped with HarfBuzz and drawn from glyph outlines."""

    def __init__(self, text: str, style: str, colours: list[tuple[str, str]] | None = None):
        path = font_path(style)
        self.font = TTFont(path)
        self.upem = self.font["head"].unitsPerEm
        self.cap = self.font["OS/2"].sCapHeight
        self.slant = math.tan(math.radians(-self.font["post"].italicAngle))
        blob = hb.Blob.from_file_path(path)
        self.hb_font = hb.Font(hb.Face(blob))
        self.text = text
        # colour runs: list of (substring, colour); default single colour
        self.colours = colours or [(text, NAVY)]

    def glyphs(self, tracking: float = 0):
        buf = hb.Buffer()
        buf.add_str(self.text)
        buf.guess_segment_properties()
        hb.shape(self.hb_font, buf, {"kern": True, "liga": True})
        x = 0.0
        order = self.font.getGlyphOrder()
        for info, pos in zip(buf.glyph_infos, buf.glyph_positions):
            yield order[info.codepoint], info.cluster, x + pos.x_offset
            x += pos.x_advance + tracking

    def ink_width(self, tracking: float = 0) -> tuple[float, float]:
        """Left and right ink extent at the baseline-independent level (font units)."""
        gs = self.font.getGlyphSet()
        from fontTools.pens.boundsPen import BoundsPen
        xmin, xmax = math.inf, -math.inf
        for name, _, x in self.glyphs(tracking):
            pen = BoundsPen(gs)
            gs[name].draw(pen)
            if pen.bounds:
                xmin = min(xmin, x + pen.bounds[0])
                xmax = max(xmax, x + pen.bounds[2])
        return xmin, xmax

    def ascender_height(self) -> float:
        """Highest ink above the baseline over the line (font units)."""
        from fontTools.pens.boundsPen import BoundsPen
        gs = self.font.getGlyphSet()
        top = 0
        for name, _, _ in self.glyphs():
            pen = BoundsPen(gs)
            gs[name].draw(pen)
            if pen.bounds:
                top = max(top, pen.bounds[3])
        return top

    def paths(self, scale: float, left: float, baseline: float, tracking: float = 0):
        """Return {colour: path d}, with the line's ink starting at `left`."""
        gs = self.font.getGlyphSet()
        xmin, _ = self.ink_width(tracking)
        out: dict[str, str] = {}
        bounds = []
        start = 0
        for sub, colour in self.colours:
            bounds.append((start, start + len(sub), colour))
            start += len(sub)
        for name, cluster, x in self.glyphs(tracking):
            colour = next(c for a, b, c in bounds if a <= cluster < b)
            pen = SVGPathPen(gs, ntos=lambda v: f"{v:.2f}".rstrip("0").rstrip("."))
            tx = left + (x - xmin) * scale
            gs[name].draw(TransformPen(pen, (scale, 0, 0, -scale, tx, baseline)))
            out[colour] = out.get(colour, "") + pen.getCommands()
        return out


def layout() -> dict[str, str]:
    main = Line("MiniTrainStore", "ExtraBold Italic",
                [("Mini", SKY), ("Train", NAVY), ("Store", SKY)])
    tag = Line("modélisme ferroviaire", "SemiBold Italic")

    lo, hi = main.ink_width()
    scale1 = (TEXT_RIGHT - TEXT_LEFT) / (hi - lo)
    main_cap = main.cap * scale1

    # Tagline: same italic axis (left-aligned) as the main line.
    tag_top = tag.ascender_height()          # tallest glyph above the baseline (é, l, d, f)
    scale2 = scale1 * TAG_RATIO
    block = main_cap + LINE_GAP + tag_top * scale2
    baseline1 = BLOCK_CENTRE - block / 2 + main_cap
    baseline2 = baseline1 + LINE_GAP + tag_top * scale2
    shift = main.slant * (baseline2 - baseline1)
    left2 = TEXT_LEFT - shift
    tracking = TAG_TRACKING

    paths: dict[str, str] = {}
    for colour, d in main.paths(scale1, TEXT_LEFT, baseline1).items():
        paths[colour] = paths.get(colour, "") + d
    for colour, d in tag.paths(scale2, left2, baseline2, tracking).items():
        paths[colour] = paths.get(colour, "") + d
    print(f"main cap {main_cap:.1f}, baseline {baseline1:.1f}; tagline cap "
          f"{tag.cap * scale2:.1f}, baseline {baseline2:.1f}, left {left2:.1f}")
    return paths


def locomotive() -> dict[str, str]:
    source = (OUT / "locomotive.svg").read_text()
    return {
        SKY: re.search(r'id="sky"[^>]* d="([^"]+)"', source).group(1),
        NAVY: re.search(r'id="navy"[^>]* d="([^"]+)"', source).group(1),
    }


def svg(view: str, layers: list[tuple[str, str]], title: str, background: str | None = None) -> str:
    x, y, w, h = (float(v) for v in view.split())
    bg = f'<rect x="{x:g}" y="{y:g}" width="{w:g}" height="{h:g}" fill="{background}"/>' if background else ""
    body = "".join(f'<path fill="{c}" d="{d}"/>' for c, d in layers if d)
    return (f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="{view}" '
            f'width="{w:g}" height="{h:g}"><title>{title}</title>{bg}{body}</svg>\n')


def recolour(layers, mapping):
    return [(mapping.get(c, c), d) for c, d in layers]


BADGE = 512
BADGE_RADIUS = 112     # corner radius of the rounded square (about 22 %, like app icons)
BADGE_SCALE = 1.22
BODY_X, BODY_Y = 318, 104   # visual centre of the locomotive body
BADGES = {
    # file: (shape, background, recolouring of the locomotive)
    "minitrainstore-icone-rond.svg": ("rond", NAVY, {NAVY: WHITE}),
    "minitrainstore-icone-carre.svg": ("arrondi", NAVY, {NAVY: WHITE}),
    "minitrainstore-icone-carre-plein.svg": ("plein", NAVY, {NAVY: WHITE}),
    "minitrainstore-icone-carre-clair.svg": ("arrondi", WHITE, {}),
    "minitrainstore-icone-carre-ciel.svg": ("arrondi", SKY, {SKY: WHITE}),
}


# Favicon: at 16 to 48 px the whole locomotive is a few pixels, so the tile
# zooms on the nose and windscreen. Brand blue stands out on light and dark
# browser tabs, where navy disappears.
FAVICON_SCALE = 2.0
FAVICON_CENTRE = 370, 95
FAVICON_RADIUS = 96


def favicon(layers) -> str:
    cx, cy = FAVICON_CENTRE
    tx, ty = BADGE / 2 - cx * FAVICON_SCALE, BADGE / 2 - cy * FAVICON_SCALE
    body = "".join(f'<path fill="{c}" d="{d}"/>' for c, d in recolour(layers, {SKY: WHITE}))
    outline = f'<rect width="{BADGE}" height="{BADGE}" rx="{FAVICON_RADIUS}"/>'
    return (f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {BADGE} {BADGE}" '
            f'width="{BADGE}" height="{BADGE}"><title>MiniTrainStore</title>'
            f'<defs><clipPath id="tile">{outline}</clipPath></defs>'
            f'{outline.replace("/>", f' fill="{SKY}"/>')}'
            f'<g clip-path="url(#tile)"><g transform="translate({tx:.2f} {ty:.2f}) '
            f'scale({FAVICON_SCALE})">{body}</g></g></svg>\n')


def badge(layers, shape: str, background: str, mapping: dict[str, str]) -> str:
    """A square tile, rounded square or disc filled by the locomotive."""
    r = BADGE / 2
    if shape == "rond":
        outline = f'<circle cx="{r:g}" cy="{r:g}" r="{r:g}"/>'
    elif shape == "arrondi":
        outline = f'<rect width="{BADGE}" height="{BADGE}" rx="{BADGE_RADIUS}"/>'
    else:
        outline = f'<rect width="{BADGE}" height="{BADGE}"/>'
    filled = outline.replace("/>", f' fill="{background}"/>')
    tx, ty = r - BODY_X * BADGE_SCALE, r + 8 - BODY_Y * BADGE_SCALE
    body = "".join(f'<path fill="{c}" d="{d}"/>' for c, d in recolour(layers, mapping))
    return (f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {BADGE} {BADGE}" '
            f'width="{BADGE}" height="{BADGE}"><title>MiniTrainStore</title>'
            f'<defs><clipPath id="tile">{outline}</clipPath></defs>{filled}'
            f'<g clip-path="url(#tile)"><g transform="translate({tx:.2f} {ty:.2f}) '
            f'scale({BADGE_SCALE})">{body}</g></g></svg>\n')


def main() -> None:
    loco = locomotive()
    text = layout()
    layers = [(SKY, loco[SKY]), (NAVY, loco[NAVY]), (SKY, text.get(SKY, "")), (NAVY, text.get(NAVY, ""))]
    pad = 12
    view = f"{-pad} {-pad} {1050 + 2 * pad} {213 + 2 * pad}"
    title = "MiniTrainStore, modélisme ferroviaire"
    files = {
        "minitrainstore-logo.svg": svg(view, layers, title),
        "minitrainstore-logo-marine.svg": svg(view, recolour(layers, {SKY: NAVY}), title),
        "minitrainstore-logo-blanc.svg": svg(view, recolour(layers, {SKY: WHITE, NAVY: WHITE}), title),
        "minitrainstore-logo-sur-marine.svg": svg(view, recolour(layers, {NAVY: WHITE}), title, NAVY),
    }
    # Locomotive alone (whole nose and headlight), swoosh cut on a slant past the nose.
    icon_layers = [(SKY, loco[SKY]), (NAVY, loco[NAVY])]
    cut = '<clipPath id="cut"><path d="M-20 -20H560L620 240H-20Z"/></clipPath>'
    def symbol(layers_):
        body = "".join(f'<path fill="{c}" d="{d}"/>' for c, d in layers_)
        return (f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="-12 -12 644 237" width="644" height="237">'
                f'<title>MiniTrainStore</title><defs>{cut}</defs><g clip-path="url(#cut)">{body}</g></svg>\n')
    files["minitrainstore-locomotive.svg"] = symbol(icon_layers)
    files["minitrainstore-locomotive-marine.svg"] = symbol(recolour(icon_layers, {SKY: NAVY}))

    # Badges (avatars, app icons, stickers): the locomotive fills a 512 px
    # tile, which crops the speed lines and the swoosh.
    for name, (shape, background, mapping) in BADGES.items():
        files[name] = badge(icon_layers, shape, background, mapping)
    files["minitrainstore-favicon.svg"] = favicon(icon_layers)
    for name, content in files.items():
        (OUT / name).write_text(content, encoding="utf-8")
    cairosvg.svg2png(bytestring=files["minitrainstore-logo.svg"].encode(),
                     write_to=str(OUT / "minitrainstore-logo.png"), output_width=2148)
    for name in BADGES:
        cairosvg.svg2png(bytestring=files[name].encode(),
                         write_to=str(OUT / name.replace(".svg", ".png")), output_width=512)
    cairosvg.svg2png(bytestring=files["minitrainstore-locomotive.svg"].encode(),
                     write_to=str(OUT / "minitrainstore-locomotive.png"), output_width=1288)
    # Each favicon size is rendered from the vector, not downscaled from 512 px.
    sizes = (16, 32, 48)
    frames = [Image.open(io.BytesIO(cairosvg.svg2png(
        bytestring=files["minitrainstore-favicon.svg"].encode(), output_width=size)))
        for size in sizes]
    frames[-1].save(OUT / "minitrainstore-favicon.ico", sizes=[(s, s) for s in sizes],
                    append_images=frames[:-1])
    cairosvg.svg2png(bytestring=files["minitrainstore-favicon.svg"].encode(),
                     write_to=str(OUT / "minitrainstore-favicon.png"), output_width=192)
    print("Logo files written to", OUT.relative_to(ROOT))


if __name__ == "__main__":
    main()
