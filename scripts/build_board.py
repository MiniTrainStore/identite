#!/usr/bin/env python3
"""Compose the identity board: logo, colours, font, icons and cards on one page.

A page to show the identity at a glance (to print or send). Text is drawn from
the Montserrat outlines, like the logo, so the SVG renders the same anywhere.

    uv run scripts/build_board.py

Run it after scripts/build_logo.py and scripts/generate_cards.py: the board
embeds their outputs.
"""
from __future__ import annotations

import base64
from functools import lru_cache
from pathlib import Path
import re

import cairosvg

from build_logo import NAVY, SKY, WHITE, Line

ROOT = Path(__file__).resolve().parents[1]
RES = ROOT / "ressources"
LOGO = RES / "logo"
PAPER, MUTED, RULE = "#f5f0f0", "#4d6578", "#cdd8dc"
TAB_BAR, TAB = "#2b2a33", "#42414d"

W, M = 1600, 110                 # page width, side margin
CONTENT = W - 2 * M


@lru_cache(maxsize=None)
def line(text: str, style: str, colours: tuple[tuple[str, str], ...]) -> Line:
    return Line(text, style, list(colours))


def text(s: str, size: float, x: float, y: float, style: str = "Medium",
         colour: str = NAVY, anchor: str = "start", tracking: float = 0,
         colours: list[tuple[str, str]] | None = None) -> str:
    """Outlined text; `y` is the baseline, `tracking` is in em."""
    ln = line(s, style, tuple(colours or [(s, colour)]))
    scale = size / ln.upem
    track = tracking * ln.upem
    lo, hi = ln.ink_width(track)
    width = (hi - lo) * scale
    left = {"start": x, "middle": x - width / 2, "end": x - width}[anchor]
    return "".join(f'<path fill="{c}" d="{d}"/>'
                   for c, d in ln.paths(scale, left, y, track).items())


_embeds = 0


def embed(name: str, x: float, y: float, width: float) -> tuple[str, float]:
    """Nest one of the logo SVGs at (x, y), `width` wide. Returns (svg, height)."""
    global _embeds
    _embeds += 1
    source = (LOGO / name).read_text()
    view = re.search(r'viewBox="([^"]+)"', source).group(1)
    vx, vy, vw, vh = (float(v) for v in view.split())
    inner = re.sub(r"^.*?<svg[^>]*>|</svg>\s*$", "", source, flags=re.S)
    inner = re.sub(r"<title>.*?</title>", "", inner)
    prefix = f"e{_embeds}-"
    inner = re.sub(r'id="([^"]+)"', rf'id="{prefix}\1"', inner)
    inner = re.sub(r"url\(#([^)]+)\)", rf"url(#{prefix}\1)", inner)
    height = width * vh / vw
    return (f'<svg x="{x:g}" y="{y:g}" width="{width:g}" height="{height:g}" '
            f'viewBox="{view}">{inner}</svg>'), height


def image(path: Path, x: float, y: float, width: float, pixels: tuple[int, int]) -> tuple[str, float]:
    height = width * pixels[1] / pixels[0]
    data = base64.b64encode(path.read_bytes()).decode()
    return (f'<image x="{x:g}" y="{y:g}" width="{width:g}" height="{height:g}" '
            f'href="data:image/png;base64,{data}"/>'), height


def png_size(path: Path) -> tuple[int, int]:
    header = path.read_bytes()[16:24]
    return int.from_bytes(header[:4], "big"), int.from_bytes(header[4:], "big")


def rect(x, y, w, h, fill, rx=0, stroke=None) -> str:
    border = f' stroke="{stroke}" stroke-width="2"' if stroke else ""
    return f'<rect x="{x:g}" y="{y:g}" width="{w:g}" height="{h:g}" rx="{rx:g}" fill="{fill}"{border}/>'


def heading(title: str, subtitle: str, y: float) -> str:
    return (text(title, 44, M, y, "Bold") +
            text(subtitle, 24, M, y + 44, "Medium", MUTED))


def build() -> str:
    parts: list[str] = []
    add = parts.append

    # Header: the logo, large.
    add(text("IDENTITÉ VISUELLE", 22, W / 2, 112, "SemiBold", SKY, "middle", .18))
    logo, h = embed("minitrainstore-logo.svg", (W - 1120) / 2, 150, 1120)
    add(logo)
    add(text("minitrainstore.fr", 28, W / 2, 150 + h + 60, "Medium", MUTED, "middle"))
    add(f'<path d="M{M} 540H{W - M}" stroke="{RULE}" stroke-width="2"/>')

    # Colours.
    y = 630
    add(heading("Les couleurs", "Trois couleurs, reprises du site", y))
    swatches = [
        ("Bleu marine", NAVY, WHITE, "Le texte et la locomotive"),
        ("Bleu ciel", SKY, WHITE, "Les accents et la vitesse"),
        ("Papier", PAPER, NAVY, "Le fond du site et des cartes"),
    ]
    gap = 40
    sw = (CONTENT - 2 * gap) / 3
    top = y + 90
    for i, (name, fill, ink, use) in enumerate(swatches):
        x = M + i * (sw + gap)
        add(rect(x, top, sw, 240, fill, 24, RULE if fill == PAPER else None))
        add(text(name, 34, x + 32, top + 70, "SemiBold", ink))
        add(text(fill.upper(), 24, x + 32, top + 110, "Medium", ink))
        add(text(use, 22, x, top + 240 + 42, "Medium", MUTED))

    # Font.
    y = top + 240 + 140
    add(heading("La police : Montserrat", "Celle du site, moderne et très lisible", y))
    add(text("MiniTrainStore", 96, M, y + 180, "ExtraBold Italic",
             colours=[("Mini", SKY), ("Train", NAVY), ("Store", SKY)]))
    add(text("modélisme ferroviaire", 48, M, y + 250, "SemiBold Italic"))
    add(text("Locomotives, wagons, voies et accessoires", 30, M, y + 320, "Medium"))
    add(text("Aa Bb Cc Dd Ee Ff Gg  0 1 2 3 4 5 6 7 8 9", 30, M, y + 370, "Regular", MUTED))

    # Logo on several backgrounds.
    y += 470
    add(heading("Le logo sur différents fonds", "Il s'adapte à tous les supports", y))
    tiles = [
        ("minitrainstore-logo.svg", WHITE, "En couleurs"),
        ("minitrainstore-logo-sur-marine.svg", NAVY, "Sur fond marine"),
        ("minitrainstore-logo-blanc.svg", SKY, "Sur fond bleu ciel"),
        ("minitrainstore-logo-marine.svg", WHITE, "En une couleur, pour un tampon"),
    ]
    tw, th = (CONTENT - gap) / 2, 230
    top = y + 90
    for i, (name, fill, caption) in enumerate(tiles):
        x = M + (i % 2) * (tw + gap)
        ty = top + (i // 2) * (th + 80)
        add(rect(x, ty, tw, th, fill, 24, RULE if fill == WHITE else None))
        lw = 540
        _, lh = embed(name, 0, 0, lw)
        logo, _ = embed(name, x + (tw - lw) / 2, ty + (th - lh) / 2, lw)
        add(logo)
        add(text(caption, 22, x, ty + th + 40, "Medium", MUTED))

    # Icons.
    y = top + 2 * (th + 80) + 90
    add(heading("Les icônes", "Pour les avatars, les réseaux et le navigateur", y))
    icons = [
        ("minitrainstore-icone-rond.svg", "Pastille ronde", "Avatar leboncoin"),
        ("minitrainstore-icone-carre.svg", "Carré marine", "Application, réseaux"),
        ("minitrainstore-icone-carre-clair.svg", "Carré clair", "Sur fond sombre"),
        ("minitrainstore-icone-carre-ciel.svg", "Carré ciel", "Visuels promotionnels"),
        ("minitrainstore-favicon.svg", "Favicon", "Onglet du navigateur"),
    ]
    size = 220
    igap = (CONTENT - len(icons) * size) / (len(icons) - 1)
    top = y + 90
    for i, (name, label, use) in enumerate(icons):
        x = M + i * (size + igap)
        icon, _ = embed(name, x, top, size)
        add(icon)
        add(text(label, 24, x + size / 2, top + size + 44, "SemiBold", NAVY, "middle"))
        add(text(use, 20, x + size / 2, top + size + 76, "Medium", MUTED, "middle"))

    # The favicon at its real size, in a browser tab.
    bar = top + size + 130
    add(rect(M, bar, 560, 64, TAB_BAR, 14))
    add(rect(M + 10, bar + 10, 340, 44, TAB, 9))
    favicon, _ = embed("minitrainstore-favicon.svg", M + 26, bar + 20, 24)
    add(favicon)
    add(text("Mini Train Store", 22, M + 64, bar + 40, "Medium", WHITE))
    add(text("Taille réelle, dans l'onglet du navigateur", 22, M + 600, bar + 40, "Medium", MUTED))

    # Cards.
    y = bar + 64 + 130
    add(heading("Les cartes", "Carte de visite et carte de remerciement glissée dans les colis", y))
    top = y + 90
    for folder, label in (("cartes-de-visite", "Carte de visite"),
                          ("cartes-expedition", "Carte de remerciement, dans les colis")):
        preview = RES / folder / "minitrainstore-apercu.png"
        add(text(label, 26, M, top + 30, "SemiBold"))
        picture, ph = image(preview, M, top + 50, CONTENT, png_size(preview))
        add(picture)
        top += 50 + ph + 50

    # Footer.
    footer = top + 40
    add(rect(0, footer, W, 230, NAVY))
    logo, lh = embed("minitrainstore-logo-sur-marine.svg", (W - 520) / 2, footer + 40, 520)
    add(logo)
    add(text("minitrainstore.fr", 26, W / 2, footer + 40 + lh + 40, "Medium", WHITE, "middle"))
    height = footer + 230

    return (f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {W} {height:g}" '
            f'width="{W}" height="{height:g}"><title>Mini Train Store, identité visuelle</title>'
            f'{rect(0, 0, W, height, PAPER)}{"".join(parts)}</svg>\n')


def main() -> None:
    board = build()
    (RES / "planche-identite.svg").write_text(board, encoding="utf-8")
    cairosvg.svg2png(bytestring=board.encode(), write_to=str(RES / "planche-identite.png"),
                     output_width=W, unsafe=True)
    print("Identity board written to ressources/planche-identite.{svg,png}")


if __name__ == "__main__":
    main()
