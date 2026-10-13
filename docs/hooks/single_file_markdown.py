"""MkDocs hook: write the Markdown of every nav page into a single file.

Only pages in `nav` are included, in navigation order (`not_in_nav` pages
are left out). See https://github.com/vitalik/django-ninja/issues/1708
"""

from pathlib import Path
from typing import Any, List

from mkdocs.config.defaults import MkDocsConfig
from mkdocs.structure.files import Files
from mkdocs.structure.nav import Navigation
from mkdocs.structure.pages import Page

OUTPUT_FILE = "llms-full.txt"

_pages: List[Page] = []


def on_nav(nav: Navigation, config: MkDocsConfig, files: Files, **kwargs: Any) -> None:
    # Replaced on every build, since `mkdocs serve` keeps this module loaded.
    # Skip nav pages excluded from the site (e.g. `draft_docs`).
    _pages[:] = [page for page in nav.pages if not page.file.inclusion.is_excluded()]


def on_post_build(config: MkDocsConfig, **kwargs: Any) -> None:
    head = f"# {config.site_name}\n"
    if config.site_description:
        head += f"\n> {config.site_description}\n"
    head += "\n## Pages\n\n"

    toc = []
    sections = []
    # 1-based line of the first `<!-- source -->` line, after the TOC and a blank line.
    line = head.count("\n") + len(_pages) + 2
    for page in _pages:
        # canonical_url is None when site_url is unset; fall back to the source path.
        source = page.canonical_url or page.file.src_uri
        text = page.file.content_string.strip()
        section = f"\n<!-- source: {source} -->\n\n{text}\n"
        # Title from the H1: page.title is HTML-escaped and unset on --dirty builds.
        first_line = text.split("\n", 1)[0]
        title = first_line[2:] if first_line.startswith("# ") else page.file.src_uri
        toc.append(f"- [{title}]({source}): line {line}\n")
        sections.append(section)
        line += section.count("\n")

    content = head + "".join(toc) + "".join(sections)
    Path(config.site_dir, OUTPUT_FILE).write_text(content, encoding="utf-8")
