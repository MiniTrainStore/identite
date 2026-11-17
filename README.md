<h1 align="center"><a href="https://www.minitrainstore.fr/">Mini Train Store</a> : identité</h1>

Visual identity of [Mini Train Store](https://www.minitrainstore.fr/): logo, icon, business and shipping cards, category artwork, and the scripts that build their print-ready exports.

## Structure

- `ressources/logo.svg`, `ressources/icon.svg`, `ressources/logo/`: logo and icon.
- `ressources/cartes-de-visite/`, `ressources/cartes-expedition/`: business and shipping cards (SVG sources, PDF for the printer, A4 sheets, previews). Read `LIRE-AVANT-IMPRESSION.txt` before printing.
- `ressources/categories/`: category artwork.
- `scripts/`: `build_logo.py`, `build_card_sources.py` and `generate_cards.py`, run by the [card assets workflow](.github/workflows/card-assets.yml) on every change to regenerate the exports.

The shop's colour palette (liveries of French rolling stock) is described in the shop's design documentation, in the private [boutique](https://github.com/MiniTrainStore/boutique) repository.

Part of the [espace-de-travail](https://github.com/MiniTrainStore/espace-de-travail) of Mini Train Store.

## About

All rights reserved to [Alix ANNERAUD](https://alix.anneraud.fr/).
