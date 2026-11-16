#!/usr/bin/env python3
"""Compose the SVG masters of the business card and the shipping card.

Both cards share one graphic system (website colours and Montserrat font, navy
band with a sky tab, rail track, Nimbus Roman Italic / Z003 accents). Edit the layout
here, then run:

    python -m pip install segno
    python scripts/build_card_sources.py      # SVG masters
    python scripts/generate_cards.py          # PDF, A4 sheets, previews, ZIP

The editable SVGs keep live text. When Inkscape is available, the business
card's main SVGs are also written with text converted to paths.
"""
from __future__ import annotations

from pathlib import Path
import math
import re
import shutil
import subprocess
import tempfile

import segno

ROOT = Path(__file__).resolve().parents[1]
RESOURCES = ROOT / "ressources"
LOGO = RESOURCES / "logo-horizontal.svg"
URL = "https://www.minitrainstore.fr/"
# One utm_source per card, so Umami's UTM report tells which card brings visits.
URL_BUSINESS = URL + "?utm_source=carte-visite"
URL_SHIPPING = URL + "?utm_source=carte-colis"
SITE = "minitrainstore.fr"
EMAIL = "arnaud@minitrainstore.fr"
PHONE = "06 06 43 83 44"

# Design tokens (millimetres, colours and font of the shop website).
NAVY = "#133a57"
SKY = "#31aadf"
PAPER = "#f5f0f0"  # --o-color-3 of minitrainstore.fr
MUTED = "#4d6578"
RULE = "#cdd8dc"
WRITING_LINE = "#c9d9e0"
SANS = "Montserrat,DejaVu Sans,Arial,sans-serif"  # font of minitrainstore.fr
SERIF_ITALIC = "Nimbus Roman,Times New Roman,serif"
SCRIPT = "Z003,URW Chancery L,cursive"
W, H, BLEED = 85, 55, 3
MARGIN = 6

LOGO_W, LOGO_H = 1050, 214


def logo(x: float, y: float, width: float) -> str:
    paths = re.findall(r"<path [^>]+/>", LOGO.read_text())
    scale = width / LOGO_W
    return (
        f'<g aria-label="MiniTrainStore, modélisme ferroviaire" '
        f'transform="translate({x:g} {y:g}) scale({scale:.6f})">'
        + "".join(paths) + "</g>"
    )


def logo_centered(y: float, width: float) -> str:
    return logo((W - width) / 2, y, width)


def qr(url: str, x: float, y: float, size: float) -> str:
    """QR code as a single vector path, modules only (paper as quiet zone)."""
    code = segno.make(url, error="m", micro=False)
    matrix = list(code.matrix_iter(scale=1, border=0))
    module = size / len(matrix)
    runs = []
    for row, line in enumerate(matrix):
        col = 0
        while col < len(line):
            if line[col]:
                start = col
                while col < len(line) and line[col]:
                    col += 1
                runs.append(f"M{start} {row}h{col - start}v1h{start - col}z")
            else:
                col += 1
    return (
        f'<path aria-label="QR code vers {url}" fill="{NAVY}" '
        f'transform="translate({x:g} {y:g}) scale({module:.6f})" '
        f'd="{"".join(runs)}"/>'
    )


def band() -> str:
    return (
        f'<rect x="-3" y="-3" width="91" height="5.1" fill="{NAVY}"/>'
        f'<rect x="{MARGIN}" y="2.1" width="15" height=".75" fill="{SKY}"/>'
    )


def rails(y: float, opacity: float = 1) -> str:
    """Straight track running into the bottom bleed: sky sleepers, navy rails."""
    sleepers = "".join(
        f"M{x:.2f} {y:g}v{H + BLEED - y:g}" for x in (-2.5 + 3.6 * i for i in range(26))
    )
    return (
        f'<g opacity="{opacity:g}" fill="none">'
        f'<path d="{sleepers}" stroke="{SKY}" stroke-width=".75"/>'
        f'<path d="M-3 {y + .8:g}H88M-3 {y + 2.4:g}H88" '
        f'stroke="{NAVY}" stroke-width=".4"/></g>'
    )


def stars(cx: float, cy: float, radius: float, count: int = 5) -> str:
    """Row of five-pointed stars centred on (cx, cy)."""
    step = radius * 2.5
    shapes = []
    for i in range(count):
        x0 = cx + (i - (count - 1) / 2) * step
        points = []
        for k in range(10):
            r = radius if k % 2 == 0 else radius * .45
            angle = math.pi * (-.5 + k / 5)
            points.append(f"{x0 + r * math.cos(angle):.3f},{cy + r * math.sin(angle):.3f}")
        shapes.append("M" + "L".join(points) + "Z")
    return f'<path fill="{SKY}" d="{"".join(shapes)}"/>'


def sparks(cx: float, cy: float, gap: float, size: float = 1) -> str:
    """Little burst marks on both sides of a script title."""
    s = size
    left = (
        f"M{cx - gap:g} {cy - 2.4 * s:g}l{-2.1 * s:g} {-1.1 * s:g}"
        f"M{cx - gap:g} {cy:g}l{-2.4 * s:g} 0"
        f"M{cx - gap:g} {cy + 2.4 * s:g}l{-2.1 * s:g} {1.1 * s:g}"
    )
    right = (
        f"M{cx + gap:g} {cy - 2.4 * s:g}l{2.1 * s:g} {-1.1 * s:g}"
        f"M{cx + gap:g} {cy:g}l{2.4 * s:g} 0"
        f"M{cx + gap:g} {cy + 2.4 * s:g}l{2.1 * s:g} {1.1 * s:g}"
    )
    return (
        f'<path d="{left}{right}" fill="none" stroke="{SKY}" '
        f'stroke-width="{.55 * s:g}" stroke-linecap="round"/>'
    )


def text(x, y, content, size, *, family=SANS, weight="400", fill=NAVY,
         anchor="start", spacing=0, style="normal") -> str:
    attrs = [
        f'x="{x:g}"', f'y="{y:g}"', f'font-family="{family}"',
        f'font-size="{size:g}"', f'fill="{fill}"',
    ]
    if weight != "400":
        attrs.append(f'font-weight="{weight}"')
    if style != "normal":
        attrs.append(f'font-style="{style}"')
    if anchor != "start":
        attrs.append(f'text-anchor="{anchor}"')
    if spacing:
        attrs.append(f'letter-spacing="{spacing:g}"')
    escaped = content.replace("&", "&amp;")
    return f"<text {' '.join(attrs)}>{escaped}</text>"


def svg(title: str, body: list[str]) -> str:
    return (
        '<svg xmlns="http://www.w3.org/2000/svg" width="85mm" height="55mm" '
        f'viewBox="0 0 85 55" role="img" aria-label="{title}">\n'
        f"<title>{title}</title>\n"
        f'<rect x="-3" y="-3" width="91" height="61" fill="{PAPER}"/>\n'
        + "\n".join(body) + "\n</svg>\n"
    )


# --- Carte de visite -------------------------------------------------------

def business_recto() -> str:
    return svg("Mini Train Store, carte de visite, recto", [
        band(),
        logo_centered(9.4, 62),
        text(42.5, 30.2, "Par un passionné,", 4.3,
             family=SERIF_ITALIC, style="italic", anchor="middle"),
        text(42.5, 35.3, "pour les passionnés.", 4.3,
             family=SERIF_ITALIC, style="italic", anchor="middle"),
        stars(42.5, 39.5, .8),
        text(42.5, 42.7, "plus de 1 500 avis clients sur leboncoin", 1.7,
             fill=MUTED, anchor="middle"),
        text(42.5, 47.3, SITE, 2.7, weight="700", anchor="middle",
             spacing=.12),
        rails(51.2),
    ])


def business_verso() -> str:
    qr_size, qr_x, qr_y = 17, W - MARGIN - 17, 27.6
    return svg("Mini Train Store, carte de visite, verso", [
        band(),
        text(MARGIN, 11.6, "MODÉLISME FERROVIAIRE", 3.1, weight="700",
             spacing=.22),
        text(MARGIN, 17.4, "Matériel d’occasion restauré avec soin.", 2.6),
        text(MARGIN, 21.2, "Locomotives, voitures, wagons & accessoires.",
             2.3, fill=MUTED),
        f'<path d="M{MARGIN} 24.8H{W - MARGIN}" stroke="{RULE}" '
        'stroke-width=".2"/>',
        text(MARGIN, 30.4, "CONTACT & BOUTIQUE EN LIGNE", 1.75,
             weight="600", fill=SKY, spacing=.3),
        f'<text x="{MARGIN}" y="35.4" font-family="{SANS}" font-size="3.2" '
        f'fill="{NAVY}"><tspan font-weight="700">Arnaud</tspan>'
        f'<tspan font-size="2.3" fill="{MUTED}">, fondateur</tspan></text>',
        text(MARGIN, 39.9, EMAIL, 2.45),
        text(MARGIN, 43.7, PHONE, 2.45, spacing=.08),
        text(MARGIN, 47.5, SITE, 2.45),
        qr(URL_BUSINESS, qr_x, qr_y, qr_size),
        text(qr_x + qr_size / 2, qr_y + qr_size + 3.1, "Scannez & découvrez",
             1.75, fill=MUTED, anchor="middle"),
    ])


# --- Carte d'expédition ----------------------------------------------------

def shipping_recto() -> str:
    qr_size = 13.4
    qr_x, qr_y = W - MARGIN - qr_size, 35.2
    return svg("Mini Train Store, carte de remerciement, recto", [
        band(),
        logo_centered(5.4, 34),
        text(42.5, 22.6, "Merci !", 8.6, family=SCRIPT, style="italic",
             anchor="middle"),
        sparks(42.5, 19.2, 14.5, .85),
        text(42.5, 27.4, "Merci pour votre commande et votre confiance.",
             2.3, anchor="middle"),
        text(42.5, 30.6, "Beaucoup de plaisir avec votre train miniature !",
             2.05, fill=MUTED, anchor="middle"),
        f'<path d="M{MARGIN} 33.4H{W - MARGIN}" stroke="{RULE}" '
        'stroke-width=".2"/>',
        text(MARGIN, 38.1, "UN AVIS, UNE QUESTION, UN SOUCI ?", 1.6,
             weight="600", fill=SKY, spacing=.22),
        text(MARGIN, 42.4, "N’hésitez pas à m’écrire.",
             2.35, family=SERIF_ITALIC, style="italic"),
        text(MARGIN, 47.1, SITE, 2.6, weight="700"),
        text(MARGIN, 50.6, f"{EMAIL}  ·  {PHONE}", 2.05),
        qr(URL_SHIPPING, qr_x, qr_y, qr_size),
        text(qr_x + qr_size / 2, qr_y + qr_size + 2.5, "Visitez la boutique",
             1.5, fill=MUTED, anchor="middle"),
    ])


def shipping_verso() -> str:
    lines = "".join(f"M{MARGIN + 2} {y:g}H{W - MARGIN - 2}" for y in (27, 33.4, 39.8))
    return svg("Mini Train Store, carte de remerciement, verso", [
        band(),
        logo_centered(5.4, 24),
        text(42.5, 18.6, "Un petit mot pour vous…", 4.4, family=SCRIPT,
             style="italic", anchor="middle"),
        sparks(42.5, 17.2, 23.5, .55),
        f'<path d="{lines}" fill="none" stroke="{WRITING_LINE}" '
        'stroke-width=".15"/>',
        text(W - MARGIN - 2, 46.4, "Le monde du train miniature", 2.5,
             family=SERIF_ITALIC, style="italic", anchor="end"),
        rails(51.2, .5),
    ])


def outline_text(source: Path, target: Path) -> bool:
    """Write a font-independent copy using Inkscape, if installed."""
    inkscape = shutil.which("inkscape")
    if not inkscape:
        return False
    with tempfile.TemporaryDirectory() as tmp:
        out = Path(tmp) / target.name
        subprocess.run(
            [inkscape, str(source), "--export-text-to-path",
             "--export-plain-svg", f"--export-filename={out}"],
            check=True, capture_output=True,
        )
        target.write_bytes(out.read_bytes())
    return True


def main() -> None:
    cards = {
        "cartes-de-visite": (business_recto, business_verso, True),
        "cartes-expedition": (shipping_recto, shipping_verso, False),
    }
    for folder, (recto, verso, outline) in cards.items():
        base = RESOURCES / folder
        editable = base / "sources-editables"
        editable.mkdir(exist_ok=True)
        for face, build in (("recto", recto), ("verso", verso)):
            source = editable / f"minitrainstore-{face}.svg"
            source.write_text(build(), encoding="utf-8")
            main_svg = base / f"minitrainstore-{face}.svg"
            if not (outline and outline_text(source, main_svg)):
                main_svg.write_text(source.read_text(encoding="utf-8"),
                                    encoding="utf-8")
    print("SVG masters written.")


if __name__ == "__main__":
    main()
