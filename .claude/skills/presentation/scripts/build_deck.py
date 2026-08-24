#!/usr/bin/env python3
"""Fill the deck template from a pyramid spec.

    python scripts/build_deck.py <spec.json> -o presentations/<slug>.pptx

The spec is the pyramid, serialised. Every slide type below maps to one node of it:
the governing thought at the top, one `section` per supporting argument, and the
evidence slides that sit under each argument. See references/deck-spec.md.

Nothing about the look lives in this file - colours, fonts, sizes and the grid all
come from assets/theme.json, so re-skinning the deck never means editing code.
"""
from __future__ import annotations

import argparse
import json
import pathlib
import sys

from pptx import Presentation
from pptx.dml.color import RGBColor
from pptx.enum.shapes import MSO_SHAPE
from pptx.enum.text import MSO_ANCHOR, PP_ALIGN
from pptx.util import Emu, Inches, Pt

HERE = pathlib.Path(__file__).resolve().parent
SKILL = HERE.parent

CONTENT_TYPES = {"chart", "bullets", "two_col", "table", "kpi", "next_steps", "appendix"}


class Deck:
    def __init__(self, template: pathlib.Path, theme: dict, meta: dict):
        self.prs = Presentation(str(template))
        self.c = theme["colors"]
        self.s = theme["sizes"]
        self.f = theme["fonts"]
        self.g = theme["grid"]
        self.meta = meta
        self.width = self.prs.slide_width.inches
        self.height = self.prs.slide_height.inches
        self.content_w = self.width - self.g["margin_left_in"] - self.g["margin_right_in"]
        self.page = 0

    # ---------- primitives ----------

    def rgb(self, key: str) -> RGBColor:
        return RGBColor.from_string(self.c[key])

    def layout(self, name: str):
        for lay in self.prs.slide_layouts:
            if lay.name == name:
                return lay
        raise SystemExit(
            f"template has no layout named {name!r}; layouts present: "
            + ", ".join(l.name for l in self.prs.slide_layouts)
        )

    def slide(self, layout_name: str):
        return self.prs.slides.add_slide(self.layout(layout_name))

    def box(self, slide, left, top, width, height):
        tb = slide.shapes.add_textbox(Inches(left), Inches(top), Inches(width), Inches(height))
        tf = tb.text_frame
        tf.word_wrap = True
        tf.margin_left = tf.margin_right = tf.margin_top = tf.margin_bottom = 0
        return tf

    def para(self, tf, text, size, color, *, bold=False, first=False,
             font=None, space_after=6, line_spacing=None, align=None, indent_level=0):
        p = tf.paragraphs[0] if first else tf.add_paragraph()
        p.text = str(text)
        p.space_after = Pt(space_after)
        if indent_level:
            pPr = p._p.get_or_add_pPr()
            pPr.set("marL", str(int(Inches(0.34 * indent_level))))
            pPr.set("indent", "0")
        if line_spacing:
            p.line_spacing = line_spacing
        if align:
            p.alignment = align
        for run in p.runs:
            run.font.size = Pt(size)
            run.font.bold = bold
            run.font.name = font or self.f["body"]
            run.font.color.rgb = RGBColor.from_string(self.c[color])
        return p

    def rect(self, slide, left, top, width, height, fill_key, *, shape=MSO_SHAPE.RECTANGLE):
        sh = slide.shapes.add_shape(shape, Inches(left), Inches(top), Inches(width), Inches(height))
        sh.fill.solid()
        sh.fill.fore_color.rgb = self.rgb(fill_key)
        sh.line.fill.background()
        sh.shadow.inherit = False
        return sh

    # ---------- slide chrome ----------

    def title(self, slide, text):
        ph = slide.placeholders[0]
        tf = ph.text_frame
        tf.word_wrap = True
        tf.text = text
        size = self.s["action_title"]
        for candidate in (size, size - 3, size - 6, size - 8):
            lines = self.wrapped_lines(text, candidate, self.content_w)
            if lines * candidate * 1.15 / 72 <= self.g["title_height_in"]:
                size = candidate
                break
            size = candidate
        for p in tf.paragraphs:
            p.line_spacing = 1.05
            for run in p.runs:
                run.font.size = Pt(size)
                run.font.bold = True
                run.font.name = self.f["heading"]
                run.font.color.rgb = self.rgb("text")
        self.rect(
            slide,
            self.g["margin_left_in"],
            self.g["title_top_in"] + self.g["title_height_in"] + 0.06,
            1.5, 0.035, "accent",
        )

    def takeaway(self, slide, text):
        if not text:
            return
        top, h = self.g["takeaway_top_in"], self.g["takeaway_height_in"]
        self.rect(slide, self.g["margin_left_in"], top, self.content_w, h, "accent_soft")
        self.rect(slide, self.g["margin_left_in"], top, 0.045, h, "accent")
        tf = self.box(slide, self.g["margin_left_in"] + 0.28, top + 0.06, self.content_w - 0.5, h - 0.12)
        tf.vertical_anchor = MSO_ANCHOR.MIDDLE
        self.para(tf, text, self.s["takeaway"], "text", first=True, bold=True,
                  space_after=0, line_spacing=1.15)

    def footer(self, slide):
        self.page += 1
        left = self.g["margin_left_in"]
        tf = self.box(slide, left, self.g["footer_top_in"], self.content_w - 0.6, 0.3)
        label = self.meta.get("footer") or self.meta.get("title", "")
        if self.meta.get("as_of"):
            label = f"{label}  |  as of {self.meta['as_of']}"
        self.para(tf, label, self.s["footer"], "muted", first=True, space_after=0)
        num = self.box(slide, self.width - self.g["margin_right_in"] - 0.6,
                       self.g["footer_top_in"], 0.6, 0.3)
        self.para(num, str(self.page), self.s["footer"], "muted", first=True,
                  space_after=0, align=PP_ALIGN.RIGHT)

    def body_frame(self, has_takeaway: bool):
        """(top, height) of the usable body band."""
        top = self.g["body_top_in"]
        bottom = (self.g["takeaway_top_in"] - 0.2) if has_takeaway else (self.g["footer_top_in"] - 0.2)
        return top, bottom - top

    def content_slide(self, node):
        slide = self.slide("Title Only")
        self.title(slide, node["title"])
        return slide

    def finish(self, slide, node):
        self.takeaway(slide, node.get("takeaway"))
        self.footer(slide)
        if node.get("notes"):
            slide.notes_slide.notes_text_frame.text = node["notes"]

    # ---------- slide types ----------

    def s_title(self, node):
        slide = self.slide("Title Slide")
        slide.placeholders[0].text_frame.text = node.get("title", self.meta.get("title", ""))
        for p in slide.placeholders[0].text_frame.paragraphs:
            for run in p.runs:
                run.font.size = Pt(self.s["deck_title"])
                run.font.bold = True
                run.font.name = self.f["heading"]
                run.font.color.rgb = self.rgb("text")
        sub = node.get("subtitle", self.meta.get("subtitle", ""))
        bits = [b for b in (sub, node.get("audience", self.meta.get("audience")),
                            node.get("date", self.meta.get("date"))) if b]
        tf = slide.placeholders[1].text_frame
        tf.word_wrap = True
        tf.text = bits[0] if bits else ""
        for p in tf.paragraphs:
            for run in p.runs:
                run.font.size = Pt(self.s["deck_subtitle"])
                run.font.name = self.f["body"]
                run.font.color.rgb = self.rgb("muted")
        if len(bits) > 1:
            meta_tf = self.box(slide, self.g["margin_left_in"], 5.45, self.content_w, 0.6)
            self.para(meta_tf, "   |   ".join(bits[1:]), self.s["body_sub"], "muted",
                      first=True, space_after=0)
        self.rect(slide, self.g["margin_left_in"], 1.95, 1.9, 0.05, "accent")
        self.page += 1  # title page is counted but not numbered
        if node.get("notes"):
            slide.notes_slide.notes_text_frame.text = node["notes"]

    def wrapped_lines(self, text, size, width_in):
        """Rough line count for `text` at `size` pt across `width_in` inches.

        Calibrated for Arial bold, with slack for ragged-right waste. Deliberately
        pessimistic: a slide that shrinks one step too far still reads, one that
        overflows into the shape below does not.
        """
        chars_per_line = max(12, int(width_in * 115 / size))
        return max(1, -(-len(text) // chars_per_line))

    def fit_statement(self, text, *, reserve, available):
        """Pick a font size for the apex statement and return (size, block height in).

        The statement must never run into the support cards below it, so it steps
        down through the size ladder until the wrapped block fits what is left.
        """
        for size in (self.s["governing"], self.s["governing"] - 4,
                     self.s["governing"] - 8, self.s["governing"] - 11):
            lines = self.wrapped_lines(text, size, self.content_w)
            block = lines * size * 1.12 / 72 + 0.2
            if block + reserve <= available:
                return size, block
        return size, max(0.5, available - reserve)

    def s_governing_thought(self, node):
        """The apex of the pyramid: one answer, with its supporting arguments named."""
        slide = self.slide("Title Only")
        self.title(slide, node.get("title", "The answer"))
        top, height = self.body_frame(bool(node.get("takeaway")))
        supports = node.get("supports", [])
        size, block = self.fit_statement(node["statement"], reserve=1.7 if supports else 0.0,
                                         available=height)
        tf = self.box(slide, self.g["margin_left_in"], top, self.content_w, block)
        self.para(tf, node["statement"], size, "text", first=True,
                  bold=True, font=self.f["heading"], line_spacing=1.12, space_after=0)

        if supports:
            cols = len(supports)
            gap = 0.28
            w = (self.content_w - gap * (cols - 1)) / cols
            y = top + block + 0.34
            h = max(1.2, (top + height) - y)
            for i, sup in enumerate(supports):
                x = self.g["margin_left_in"] + i * (w + gap)
                self.rect(slide, x, y, w, h, "band")
                self.rect(slide, x, y, w, 0.045, "accent")
                cell = self.box(slide, x + 0.22, y + 0.28, w - 0.44, h - 0.5)
                self.para(cell, f"BECAUSE {i + 1}", self.s["footer"], "accent",
                          first=True, bold=True, space_after=6)
                self.para(cell, sup, self.s["support"], "text", line_spacing=1.15, space_after=0)
        self.finish(slide, node)

    def s_section(self, node):
        slide = self.slide("Section Header")
        slide.placeholders[0].text_frame.word_wrap = True
        slide.placeholders[0].text_frame.text = node["statement"]
        for p in slide.placeholders[0].text_frame.paragraphs:
            p.line_spacing = 1.1
            for run in p.runs:
                run.font.size = Pt(self.s["section_statement"])
                run.font.bold = True
                run.font.name = self.f["heading"]
                run.font.color.rgb = self.rgb("text")
        label = node.get("label", f"ARGUMENT {node.get('number', '')}".strip())
        tf = slide.placeholders[1].text_frame
        tf.text = label.upper()
        for p in tf.paragraphs:
            for run in p.runs:
                run.font.size = Pt(self.s["section_number"])
                run.font.bold = True
                run.font.name = self.f["body"]
                run.font.color.rgb = self.rgb("accent")
        self.rect(slide, self.g["margin_left_in"], 4.7, 1.9, 0.05, "accent")
        self.footer(slide)
        if node.get("notes"):
            slide.notes_slide.notes_text_frame.text = node["notes"]

    def s_chart(self, node):
        slide = self.content_slide(node)
        top, height = self.body_frame(bool(node.get("takeaway")))
        if node.get("source"):
            height -= 0.3
        path = pathlib.Path(node["image"])
        if not path.exists():
            raise SystemExit(f"chart image not found: {path}")
        pic = slide.shapes.add_picture(str(path), Inches(self.g["margin_left_in"]), Inches(top))
        scale = min(Inches(self.content_w) / pic.width, Inches(height) / pic.height)
        pic.width, pic.height = int(pic.width * scale), int(pic.height * scale)
        pic.left = Emu(int(Inches(self.g["margin_left_in"]) + (Inches(self.content_w) - pic.width) / 2))
        pic.top = Emu(int(Inches(top) + (Inches(height) - pic.height) / 2))
        if node.get("source"):
            src = self.box(slide, self.g["margin_left_in"], top + height + 0.06,
                           self.content_w, 0.25)
            self.para(src, f"Source: {node['source']}", self.s["footer"], "muted",
                      first=True, space_after=0)
        self.finish(slide, node)

    def s_bullets(self, node):
        slide = self.content_slide(node)
        top, height = self.body_frame(bool(node.get("takeaway")))
        tf = self.box(slide, self.g["margin_left_in"], top, self.content_w, height)
        items = node["bullets"]
        size = self.s["body"] if len(items) <= 4 else self.s["body"] - 2
        for i, item in enumerate(items):
            if isinstance(item, dict):
                self.para(tf, f"▪  {item['text']}", size, "text", first=(i == 0),
                          bold=True, space_after=3, line_spacing=1.2)
                for sub in item.get("sub", []):
                    self.para(tf, f"–  {sub}", self.s["body_sub"], "muted", space_after=10,
                              line_spacing=1.2, indent_level=1)
            else:
                self.para(tf, f"▪  {item}", size, "text", first=(i == 0),
                          space_after=12, line_spacing=1.2)
        self.finish(slide, node)

    def s_two_col(self, node):
        slide = self.content_slide(node)
        top, height = self.body_frame(bool(node.get("takeaway")))
        gap = 0.4
        w = (self.content_w - gap) / 2
        for i, side in enumerate((node["left"], node["right"])):
            x = self.g["margin_left_in"] + i * (w + gap)
            tf = self.box(slide, x, top, w, height)
            first = True
            if side.get("heading"):
                self.para(tf, side["heading"].upper(), self.s["footer"] + 2,
                          "accent" if i == 0 else "highlight", first=True, bold=True,
                          space_after=10)
                first = False
            for item in side.get("bullets", []):
                self.para(tf, f"▪  {item}", self.s["body"] - 1, "text",
                          first=first, space_after=10, line_spacing=1.2)
                first = False
        self.finish(slide, node)

    def s_kpi(self, node):
        slide = self.content_slide(node)
        top, height = self.body_frame(bool(node.get("takeaway")))
        kpis = node["kpis"]
        gap = 0.3
        w = (self.content_w - gap * (len(kpis) - 1)) / len(kpis)
        h = min(2.05, height)
        y = top + (height - h) / 2
        for i, k in enumerate(kpis):
            x = self.g["margin_left_in"] + i * (w + gap)
            emphasis = k.get("emphasis", "accent")
            self.rect(slide, x, y, w, h,
                      "highlight_soft" if emphasis == "highlight" else "band")
            self.rect(slide, x, y, w, 0.05, emphasis)
            tf = self.box(slide, x + 0.24, y + 0.38, w - 0.48, h - 0.6)
            self.para(tf, k["value"], self.s["kpi_value"], emphasis, first=True,
                      bold=True, font=self.f["heading"], space_after=8)
            self.para(tf, k["label"], self.s["kpi_label"], "text", line_spacing=1.2,
                      space_after=0)
        self.finish(slide, node)

    def s_table(self, node):
        slide = self.content_slide(node)
        top, height = self.body_frame(bool(node.get("takeaway")))
        cols, rows = node["columns"], node["rows"]
        row_h = min(0.42, height / (len(rows) + 1))
        tbl_h = row_h * (len(rows) + 1)
        shape = slide.shapes.add_table(
            len(rows) + 1, len(cols),
            Inches(self.g["margin_left_in"]), Inches(top + (height - tbl_h) / 2),
            Inches(self.content_w), Inches(tbl_h),
        )
        table = shape.table
        table.first_row = True
        highlight = set(node.get("highlight_rows", []))
        for j, name in enumerate(cols):
            cell = table.cell(0, j)
            cell.text = str(name)
            self._cell(cell, self.s["table"], "text_on_accent", "accent", bold=True)
        for i, row in enumerate(rows):
            for j, value in enumerate(row):
                cell = table.cell(i + 1, j)
                cell.text = "" if value is None else str(value)
                hot = i in highlight
                self._cell(
                    cell, self.s["table"],
                    "highlight" if hot else "text",
                    "highlight_soft" if hot else ("band" if i % 2 else "background"),
                    bold=hot,
                )
        self.finish(slide, node)

    def _cell(self, cell, size, color, fill, *, bold=False):
        cell.fill.solid()
        cell.fill.fore_color.rgb = self.rgb(fill)
        cell.vertical_anchor = MSO_ANCHOR.MIDDLE
        cell.margin_left = cell.margin_right = Inches(0.12)
        for p in cell.text_frame.paragraphs:
            for run in p.runs:
                run.font.size = Pt(size)
                run.font.bold = bold
                run.font.name = self.f["body"]
                run.font.color.rgb = self.rgb(color)

    def s_next_steps(self, node):
        slide = self.content_slide(node)
        top, height = self.body_frame(bool(node.get("takeaway")))
        steps = node["steps"]
        h = min(1.0, height / max(len(steps), 1) - 0.16)
        for i, step in enumerate(steps):
            y = top + i * (h + 0.16)
            self.rect(slide, self.g["margin_left_in"], y, self.content_w, h, "band")
            self.rect(slide, self.g["margin_left_in"], y, 0.05, h, "accent")
            num = self.box(slide, self.g["margin_left_in"] + 0.24, y + 0.16, 0.5, h - 0.3)
            self.para(num, str(i + 1), self.s["body"] + 4, "accent", first=True, bold=True,
                      font=self.f["heading"], space_after=0)
            tf = self.box(slide, self.g["margin_left_in"] + 0.85, y + 0.14,
                          self.content_w - 1.2, h - 0.26)
            self.para(tf, step["action"], self.s["body"] - 1, "text", first=True,
                      bold=True, space_after=4, line_spacing=1.15)
            trailer = "   |   ".join(
                x for x in (step.get("owner"), step.get("when")) if x
            )
            if trailer:
                self.para(tf, trailer, self.s["body_sub"], "muted", space_after=0)
        self.finish(slide, node)

    def s_appendix_divider(self, node):
        slide = self.slide("Section Header")
        slide.placeholders[0].text_frame.text = node.get("statement", "Appendix")
        for p in slide.placeholders[0].text_frame.paragraphs:
            for run in p.runs:
                run.font.size = Pt(self.s["section_statement"])
                run.font.bold = True
                run.font.name = self.f["heading"]
                run.font.color.rgb = self.rgb("muted")
        tf = slide.placeholders[1].text_frame
        tf.text = node.get("label", "Backup - not part of the argument").upper()
        for p in tf.paragraphs:
            for run in p.runs:
                run.font.size = Pt(self.s["section_number"])
                run.font.bold = True
                run.font.name = self.f["body"]
                run.font.color.rgb = self.rgb("muted")
        self.rect(slide, self.g["margin_left_in"], 4.7, 1.9, 0.05, "rule")
        self.footer(slide)

    def s_appendix(self, node):
        if node.get("image"):
            return self.s_chart(node)
        if node.get("columns"):
            return self.s_table(node)
        return self.s_bullets({**node, "bullets": node.get("bullets", [])})

    # ---------- driver ----------

    def build(self, slides):
        dispatch = {
            "title": self.s_title,
            "governing_thought": self.s_governing_thought,
            "section": self.s_section,
            "chart": self.s_chart,
            "bullets": self.s_bullets,
            "two_col": self.s_two_col,
            "kpi": self.s_kpi,
            "table": self.s_table,
            "next_steps": self.s_next_steps,
            "appendix_divider": self.s_appendix_divider,
            "appendix": self.s_appendix,
        }
        for i, node in enumerate(slides):
            kind = node.get("type")
            if kind not in dispatch:
                raise SystemExit(
                    f"slide {i}: unknown type {kind!r}; known types: "
                    + ", ".join(sorted(dispatch))
                )
            dispatch[kind](node)


def lint(spec: dict) -> list:
    """Structural checks on the pyramid, reported but never fatal."""
    warn = []
    slides = spec["slides"]
    kinds = [s.get("type") for s in slides]
    if kinds[:1] != ["title"]:
        warn.append("deck does not open with a title slide")
    if "governing_thought" not in kinds:
        warn.append("no governing_thought slide - the pyramid has no apex")
    elif kinds.index("governing_thought") > 2:
        warn.append("governing thought comes late - the answer is buried")
    sections = kinds.count("section")
    if sections and not 2 <= sections <= 5:
        warn.append(f"{sections} supporting arguments - a pyramid holds up best at 3 (2-4 works)")
    apex = next((s for s in slides if s.get("type") == "governing_thought"), None)
    if apex and sections and len(apex.get("supports", [])) != sections:
        warn.append(
            f"governing thought names {len(apex.get('supports', []))} supports "
            f"but the deck has {sections} argument sections"
        )
    seen_appendix = False
    for i, s in enumerate(slides):
        if s.get("type") == "appendix_divider":
            seen_appendix = True
            continue
        if seen_appendix or s.get("type") not in CONTENT_TYPES:
            continue
        if not s.get("takeaway"):
            warn.append(f"slide {i + 1} ({s.get('title', s['type'])!r}) has no takeaway line")
        title = s.get("title", "")
        if title and len(title.split()) <= 3:
            warn.append(f"slide {i + 1} title {title!r} looks like a label, not an assertion")
    return warn


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("spec", type=pathlib.Path)
    ap.add_argument("-o", "--out", type=pathlib.Path, required=True)
    ap.add_argument("--template", type=pathlib.Path, default=SKILL / "assets" / "template.pptx")
    ap.add_argument("--theme", type=pathlib.Path, default=SKILL / "assets" / "theme.json")
    args = ap.parse_args()

    spec = json.loads(args.spec.read_text())
    theme = json.loads(args.theme.read_text())
    for message in lint(spec):
        print(f"warning: {message}", file=sys.stderr)

    deck = Deck(args.template, theme, spec.get("meta", {}))
    deck.build(spec["slides"])
    args.out.parent.mkdir(parents=True, exist_ok=True)
    deck.prs.save(str(args.out))
    print(f"wrote {args.out}  ({len(deck.prs.slides)} slides)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
