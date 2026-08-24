#!/usr/bin/env python3
"""Generate assets/template.pptx - the neutral 16:9 deck template the build script fills.

Run this only to (re)create the template, not per deck:

    python scripts/build_template.py

It reads assets/theme.json and produces a template whose theme colours, fonts and
layout geometry match it. The template keeps the four standard layouts the deck
builder uses - "Title Slide", "Section Header", "Title Only" and "Blank" - because
those four exist in virtually every corporate PowerPoint template, which is what
makes swapping in a branded file a drop-in operation.
"""
from __future__ import annotations

import json
import pathlib
import sys

from lxml import etree
from pptx import Presentation
from pptx.dml.color import RGBColor
from pptx.opc.constants import RELATIONSHIP_TYPE as RT
from pptx.util import Inches, Pt

HERE = pathlib.Path(__file__).resolve().parent
SKILL = HERE.parent
A = "http://schemas.openxmlformats.org/drawingml/2006/main"

# theme colour slot -> key in theme.json["colors"]
CLR_MAP = {
    "dk1": "text",
    "lt1": "background",
    "dk2": "text",
    "lt2": "band",
    "accent1": "accent",
    "accent2": "highlight",
    "accent3": "muted",
    "accent4": "accent_soft",
    "accent5": "rule",
    "accent6": "muted",
    "hlink": "accent",
    "folHlink": "muted",
}

# layouts we keep, by the placeholder idx values worth preserving on each
KEEP = {
    "Title Slide": {0, 1},
    "Section Header": {0, 1},
    "Title Only": {0},
    "Blank": set(),
}


def load_theme() -> dict:
    return json.loads((SKILL / "assets" / "theme.json").read_text())


def restyle_theme_part(prs, theme: dict) -> None:
    """Rewrite the theme's colour and font schemes from theme.json."""
    part = prs.slide_masters[0].part.part_related_by(RT.THEME)
    root = etree.fromstring(part.blob)

    scheme = root.find(f".//{{{A}}}clrScheme")
    if scheme is not None:
        for slot, key in CLR_MAP.items():
            node = scheme.find(f"{{{A}}}{slot}")
            if node is None:
                continue
            for child in list(node):
                node.remove(child)
            srgb = etree.SubElement(node, f"{{{A}}}srgbClr")
            srgb.set("val", theme["colors"][key])

    fonts = root.find(f".//{{{A}}}fontScheme")
    if fonts is not None:
        for tag, key in (("majorFont", "heading"), ("minorFont", "body")):
            group = fonts.find(f"{{{A}}}{tag}")
            if group is None:
                continue
            latin = group.find(f"{{{A}}}latin")
            if latin is not None:
                latin.set("typeface", theme["fonts"][key])

    blob = etree.tostring(root, xml_declaration=True, encoding="UTF-8", standalone=True)
    if hasattr(part, "_element"):
        part._element = root  # XmlPart
    else:
        part._blob = blob  # generic Part


def strip_layouts(prs, theme: dict) -> None:
    """Drop layouts we do not use and trim the placeholders on the ones we keep."""
    layouts = prs.slide_layouts
    for layout in list(layouts):
        if layout.name not in KEEP:
            layouts.remove(layout)
            continue
        keep = KEEP[layout.name]
        for ph in list(layout.placeholders):
            if ph.placeholder_format.idx not in keep:
                ph._element.getparent().remove(ph._element)


def place(ph, left, top, width, height) -> None:
    ph.left, ph.top, ph.width, ph.height = (
        Inches(left), Inches(top), Inches(width), Inches(height),
    )


def style_layouts(prs, theme: dict) -> None:
    g, c, s, f = theme["grid"], theme["colors"], theme["sizes"], theme["fonts"]
    content_w = theme["slide"]["width_in"] - g["margin_left_in"] - g["margin_right_in"]

    def font(ph, size, color, bold=False, name=None):
        p = ph.text_frame.paragraphs[0]
        p.font.size = Pt(size)
        p.font.bold = bold
        p.font.name = name or f["heading"]
        p.font.color.rgb = RGBColor.from_string(color)

    for layout in prs.slide_layouts:
        if layout.name == "Title Slide":
            place(layout.placeholders[0], g["margin_left_in"], 2.35, content_w, 1.9)
            place(layout.placeholders[1], g["margin_left_in"], 4.35, content_w, 1.1)
            font(layout.placeholders[0], s["deck_title"], c["text"], bold=True)
            font(layout.placeholders[1], s["deck_subtitle"], c["muted"], name=f["body"])
        elif layout.name == "Section Header":
            place(layout.placeholders[0], g["margin_left_in"], 2.9, content_w, 1.6)
            place(layout.placeholders[1], g["margin_left_in"], 2.4, content_w, 0.4)
            font(layout.placeholders[0], s["section_statement"], c["text"], bold=True)
            font(layout.placeholders[1], s["section_number"], c["accent"], bold=True, name=f["body"])
        elif layout.name == "Title Only":
            place(
                layout.placeholders[0],
                g["margin_left_in"], g["title_top_in"], content_w, g["title_height_in"],
            )
            font(layout.placeholders[0], s["action_title"], c["text"], bold=True)


def main() -> int:
    theme = load_theme()
    prs = Presentation()
    prs.slide_width = Inches(theme["slide"]["width_in"])
    prs.slide_height = Inches(theme["slide"]["height_in"])

    restyle_theme_part(prs, theme)
    strip_layouts(prs, theme)
    style_layouts(prs, theme)

    out = SKILL / "assets" / "template.pptx"
    prs.save(str(out))
    names = [layout.name for layout in prs.slide_layouts]
    print(f"wrote {out}")
    print(f"layouts: {', '.join(names)}")
    print(f"size: {prs.slide_width.inches:.3f} x {prs.slide_height.inches:.3f} in")
    return 0


if __name__ == "__main__":
    sys.exit(main())
