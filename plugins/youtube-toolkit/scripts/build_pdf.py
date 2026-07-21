#!/usr/bin/env python3
"""Render a timestamped screenshot recap PDF (reportlab).

Library + CLI. Items are dicts: {timestamp, section, text, image_path}. The
layout is the single source of truth for the recap PDF, reused by
screenshot_pdf.py, the MCP server, and the build_zip package.
"""
from __future__ import annotations

import json
import os
import sys


def build_pdf(items, out_path, title="YouTube Video Timestamped Recap", subtitle=None):
    from reportlab.lib import colors
    from reportlab.lib.pagesizes import letter
    from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
    from reportlab.platypus import HRFlowable, Image, Paragraph, SimpleDocTemplate, Spacer

    styles = getSampleStyleSheet()
    title_style = ParagraphStyle('DocTitle', parent=styles['Heading1'], fontSize=18, leading=22, textColor=colors.HexColor("#1A365D"))
    sub_style = ParagraphStyle('Sub', parent=styles['Normal'], fontSize=9, leading=12, textColor=colors.HexColor("#718096"))
    section_style = ParagraphStyle('SecTitle', parent=styles['Heading2'], fontSize=12, leading=15, textColor=colors.HexColor("#2B6CB0"))
    body_style = ParagraphStyle('Body', parent=styles['Normal'], fontSize=10, leading=14, textColor=colors.HexColor("#2D3748"))

    doc = SimpleDocTemplate(out_path, pagesize=letter,
                            rightMargin=40, leftMargin=40, topMargin=40, bottomMargin=40)
    story = [Paragraph(title, title_style), Spacer(1, 4)]
    if subtitle:
        story += [Paragraph(subtitle, sub_style), Spacer(1, 6)]
    story += [Spacer(1, 6),
              HRFlowable(width="100%", thickness=1, color=colors.HexColor("#CBD5E0"), spaceAfter=15)]

    current_section = None
    for item in items:
        section = item.get("section", "Recap")
        if section != current_section:
            current_section = section
            story += [Spacer(1, 10), Paragraph(current_section, section_style), Spacer(1, 5)]
        text = f"<b>Timestamp [{item.get('timestamp', 'N/A')}]:</b> {item.get('text', '')}"
        story += [Paragraph(text, body_style), Spacer(1, 8)]
        img = item.get("image_path")
        if img and os.path.exists(img):
            story += [Image(img, width=450, height=253), Spacer(1, 15)]

    doc.build(story)
    return os.path.abspath(out_path)


def main():
    import argparse
    ap = argparse.ArgumentParser(description="Build a recap PDF from a JSON item list.")
    ap.add_argument("items_json", help="Path to JSON: [{timestamp, section, text, image_path}]")
    ap.add_argument("-o", "--out", default="recap_with_screenshots.pdf")
    ap.add_argument("--title", default="YouTube Video Timestamped Recap")
    ap.add_argument("--subtitle", default=None)
    a = ap.parse_args()
    items = json.load(open(a.items_json, encoding="utf-8"))
    path = build_pdf(items, a.out, a.title, a.subtitle)
    print(f"PDF written: {path}", file=sys.stderr)
    print(path)


if __name__ == "__main__":
    main()
