# AGENTS.md

Visual identity of Mini Train Store (minitrainstore.fr), a French model railway shop: logo, icon,
business and shipping cards, category artwork, and the Python scripts that build them. Part of the
[espace-de-travail](https://github.com/MiniTrainStore/espace-de-travail) of the MiniTrainStore
organization.

## Layout

| Path | Role |
| --- | --- |
| `ressources/logo/` | Logo and icon variants. `locomotive.svg` is the traced locomotive: every logo is composed from it |
| `ressources/cartes-de-visite/`, `ressources/cartes-expedition/` | Cards: SVG masters (`minitrainstore-recto.svg`, `-verso.svg`), editable sources, and the generated exports (print PDF, A4 sheets, previews, ZIP kit) |
| `ressources/categories/` | Category images of the former Odoo shop |
| `scripts/build_logo.py` | Composes the logo from the locomotive and the Montserrat outlines (`uharfbuzz`, `fonttools`, `cairosvg`) |
| `scripts/build_card_sources.py` | Builds the SVG masters of the cards |
| `scripts/generate_cards.py` | Builds the print-ready exports from the masters (dependencies in `pyproject.toml`, managed with uv) |
| `.github/workflows/card-assets.yml` | Regenerates and commits the exports whenever a master or a script changes |

## Rules

- Edit the SVG masters or the scripts, never the generated exports: CI regenerates them. Run
  `uv run scripts/generate_cards.py` to preview locally (uv installs the dependencies
  from `pyproject.toml` and `uv.lock`).
- Text on the cards is French, with correct accents; never use the em dash (the long dash).
- The shop's palette (navy, brand blue, and the liveries of French rolling stock used as accents)
  is described in the shop's design documentation (`boutique/docs/conception/11-interface.md`):
  keep the cards consistent with it.
- Commit directly on `main`, with Conventional Commits messages in English (`feat(logo): …`,
  `chore(cards): …`). Do not mention AI tools or assistants, and add no `Co-Authored-By` or
  "Generated with" lines.
