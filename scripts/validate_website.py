#!/usr/bin/env python3
"""Validate local links, generated pages, and assets in the static website."""

from __future__ import annotations

import re
import sys
from html.parser import HTMLParser
from pathlib import Path
from urllib.parse import unquote, urlsplit


ROOT = Path(__file__).resolve().parents[1]
SITE = ROOT / "website"


class PageParser(HTMLParser):
    def __init__(self) -> None:
        super().__init__(convert_charrefs=True)
        self.ids: list[str] = []
        self.links: list[str] = []
        self.sources: list[str] = []
        self.image_alts: list[str | None] = []
        self.article_cards = 0
        self.poster_cards = 0
        self.article_figures = 0
        self.h1_count = 0

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        values = dict(attrs)
        if values.get("id"):
            self.ids.append(values["id"] or "")
        if tag == "a" and values.get("href"):
            self.links.append(values["href"] or "")
        if tag in {"img", "script"} and values.get("src"):
            self.sources.append(values["src"] or "")
        if tag == "link" and values.get("href"):
            self.sources.append(values["href"] or "")
        if tag == "img":
            self.image_alts.append(values.get("alt"))
        if tag == "h1":
            self.h1_count += 1
        if tag == "a" and "article-card" in (values.get("class") or "").split():
            self.article_cards += 1
        if tag == "a" and "poster-card" in (values.get("class") or "").split():
            self.poster_cards += 1
        if tag == "figure" and "article-figure" in (values.get("class") or "").split():
            self.article_figures += 1


def parse_page(path: Path) -> PageParser:
    parser = PageParser()
    parser.feed(path.read_text(encoding="utf-8"))
    return parser


def local_path(page: Path, raw_url: str) -> tuple[Path | None, str]:
    split = urlsplit(raw_url)
    if split.scheme or split.netloc or raw_url.startswith(("mailto:", "tel:", "javascript:")):
        return None, ""
    fragment = unquote(split.fragment)
    if not split.path:
        return page, fragment
    target = (page.parent / unquote(split.path)).resolve()
    return target, fragment


def validate() -> list[str]:
    errors: list[str] = []
    pages = sorted(SITE.rglob("*.html"))
    article_pages = sorted((SITE / "articles").glob("*.html"))
    visuals = sorted((SITE / "assets" / "visuals").glob("*.svg"))

    if len(pages) != 31:
        errors.append(f"expected 31 HTML pages, found {len(pages)}")
    if len(article_pages) != 30:
        errors.append(f"expected 30 article pages, found {len(article_pages)}")
    if len(visuals) != 66:
        errors.append(f"expected 66 copied SVGs, found {len(visuals)}")

    parsed = {page.resolve(): parse_page(page) for page in pages}
    index_parser = parsed.get((SITE / "index.html").resolve())
    if not index_parser or index_parser.article_cards != 30:
        count = index_parser.article_cards if index_parser else 0
        errors.append(f"expected 30 article cards on index, found {count}")
    if not index_parser or index_parser.poster_cards != 6:
        count = index_parser.poster_cards if index_parser else 0
        errors.append(f"expected 6 poster cards on index, found {count}")

    article_visuals: set[str] = set()
    for page in article_pages:
        parser = parsed[page.resolve()]
        relative = page.relative_to(SITE)
        if parser.h1_count != 1:
            errors.append(f"{relative}: expected one h1, found {parser.h1_count}")
        if parser.article_figures != 2:
            errors.append(
                f"{relative}: expected two article figures, found {parser.article_figures}"
            )
        for source in parser.sources:
            filename = Path(urlsplit(source).path).name
            if filename.startswith("fig-") and filename.endswith(".svg"):
                article_visuals.add(filename)
    if len(article_visuals) != 60:
        errors.append(f"expected 60 unique article figures, found {len(article_visuals)}")

    for page, parser in parsed.items():
        relative = page.relative_to(SITE)
        duplicate_ids = sorted({value for value in parser.ids if parser.ids.count(value) > 1})
        if duplicate_ids:
            errors.append(f"{relative}: duplicate ids {duplicate_ids}")
        if any(alt is None for alt in parser.image_alts):
            errors.append(f"{relative}: image without alt attribute")

        for raw_url in parser.links + parser.sources:
            target, fragment = local_path(page, raw_url)
            if target is None:
                continue
            if not target.exists():
                errors.append(f"{relative}: missing local target {raw_url}")
                continue
            if fragment and target.suffix.lower() == ".html":
                target_parser = parsed.get(target.resolve())
                if target_parser and fragment not in target_parser.ids:
                    errors.append(f"{relative}: missing fragment {raw_url}")

        source = page.read_text(encoding="utf-8")
        for line_number, line in enumerate(source.splitlines(), 1):
            if line.endswith((" ", "\t")):
                errors.append(f"{relative}:{line_number}: trailing whitespace")
        if re.search(r"\.md(?:[\"'#?])|\.\./visuals/", source):
            errors.append(f"{relative}: contains source-only Markdown or visual path")

    expected_articles = [f"{number:02d}.html" for number in range(1, 31)]
    actual_articles = [page.name for page in article_pages]
    if actual_articles != expected_articles:
        errors.append("article page numbering is incomplete or out of order")

    for required in [
        SITE / "assets" / "site.css",
        SITE / "assets" / "site.js",
        SITE / "assets" / "favicon.svg",
    ]:
        if not required.exists() or required.stat().st_size == 0:
            errors.append(f"missing required asset {required.relative_to(SITE)}")

    return errors


if __name__ == "__main__":
    failures = validate()
    if failures:
        print(f"Website validation failed with {len(failures)} issue(s):")
        for failure in failures:
            print(f" - {failure}")
        sys.exit(1)
    print(
        "Website validation passed: 31 pages, 30 article cards, "
        "60 article figures, 6 posters, 66 SVG assets, all local links resolved."
    )
