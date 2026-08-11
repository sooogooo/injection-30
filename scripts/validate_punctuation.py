#!/usr/bin/env python3
"""Validate punctuation in article sources, generated pages, and SVG text."""

from __future__ import annotations

import sys
import xml.etree.ElementTree as ET
from html.parser import HTMLParser
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
ARTICLE_DIR = ROOT / "articles"
VISUAL_DIR = ROOT / "visuals"
SITE_DIR = ROOT / "website"


def quote_error(text: str) -> str | None:
    expect_open = True
    for index, character in enumerate(text):
        if character == "“":
            if not expect_open:
                return f"unexpected opening quote at character {index + 1}"
            expect_open = False
        elif character == "”":
            if expect_open:
                return f"unexpected closing quote at character {index + 1}"
            expect_open = True
    if not expect_open:
        return "missing closing quote"
    return None


class VisibleTextParser(HTMLParser):
    def __init__(self) -> None:
        super().__init__(convert_charrefs=True)
        self.hidden_depth = 0
        self.heading_depth = 0
        self.visible: list[str] = []
        self.headings: list[str] = []
        self.accessible_text: list[str] = []

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        if tag in {"script", "style"}:
            self.hidden_depth += 1
        if tag in {"h1", "h2", "h3"}:
            self.heading_depth += 1
            self.headings.append("")
        values = dict(attrs)
        if tag == "img" and values.get("alt") is not None:
            self.accessible_text.append(values["alt"] or "")
        if tag == "meta" and values.get("content"):
            self.accessible_text.append(values["content"] or "")

    def handle_endtag(self, tag: str) -> None:
        if tag in {"script", "style"}:
            self.hidden_depth = max(0, self.hidden_depth - 1)
        if tag in {"h1", "h2", "h3"}:
            self.heading_depth = max(0, self.heading_depth - 1)

    def handle_data(self, data: str) -> None:
        if self.hidden_depth:
            return
        self.visible.append(data)
        if self.heading_depth and self.headings:
            self.headings[-1] += data


def validate() -> tuple[list[str], dict[str, int]]:
    errors: list[str] = []
    totals = {"colon": 0, "em_dash": 0, "open_quote": 0, "close_quote": 0}

    for path in sorted(ARTICLE_DIR.glob("*.md")):
        text = path.read_text(encoding="utf-8")
        relative = path.relative_to(ROOT)
        totals["colon"] += text.count("：")
        totals["em_dash"] += text.count("—")
        totals["open_quote"] += text.count("“")
        totals["close_quote"] += text.count("”")

        if "：" in text:
            errors.append(f"{relative}: contains full-width colon")
        if "—" in text:
            errors.append(f"{relative}: contains Chinese em dash")
        if '"' in text:
            errors.append(f"{relative}: contains straight double quote")
        if "," in text:
            errors.append(f"{relative}: contains ASCII comma")
        if issue := quote_error(text):
            errors.append(f"{relative}: {issue}")
        for line_number, line in enumerate(text.splitlines(), 1):
            if line.startswith("#") and any(mark in line for mark in ("：", ":", "—")):
                errors.append(f"{relative}:{line_number}: heading contains colon or em dash")

    for path in sorted(VISUAL_DIR.glob("*.svg")):
        root = ET.parse(path).getroot()
        visible_text = "".join(root.itertext())
        relative = path.relative_to(ROOT)
        if "：" in visible_text:
            errors.append(f"{relative}: visible SVG text contains full-width colon")
        if "—" in visible_text:
            errors.append(f"{relative}: visible SVG text contains Chinese em dash")
        if '"' in visible_text:
            errors.append(f"{relative}: visible SVG text contains straight double quote")
        if issue := quote_error(visible_text):
            errors.append(f"{relative}: {issue}")

    for path in sorted(SITE_DIR.rglob("*.html")):
        parser = VisibleTextParser()
        parser.feed(path.read_text(encoding="utf-8"))
        visible_text = "".join(parser.visible)
        accessible_text = "".join(parser.accessible_text)
        all_user_text = visible_text + accessible_text
        relative = path.relative_to(ROOT)

        if "：" in all_user_text:
            errors.append(f"{relative}: visible or accessible text contains full-width colon")
        if "—" in all_user_text:
            errors.append(f"{relative}: visible or accessible text contains Chinese em dash")
        if '"' in all_user_text:
            errors.append(f"{relative}: visible or accessible text contains straight double quote")
        if issue := quote_error(all_user_text):
            errors.append(f"{relative}: {issue}")
        for heading in parser.headings:
            if any(mark in heading for mark in ("：", ":", "—")):
                errors.append(f"{relative}: heading contains colon or em dash: {heading.strip()}")

    return errors, totals


if __name__ == "__main__":
    failures, counts = validate()
    if failures:
        print(f"Punctuation validation failed with {len(failures)} issue(s):")
        for failure in failures:
            print(f" - {failure}")
        sys.exit(1)
    print(
        "Punctuation validation passed: "
        f"{counts['colon']} article colons, {counts['em_dash']} article em dashes, "
        f"{counts['open_quote']} opening quotes, {counts['close_quote']} closing quotes; "
        "all quotes paired and all headings clear."
    )
