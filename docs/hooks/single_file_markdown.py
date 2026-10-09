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
    parts = [f"# {config.site_name}\n"]
    if config.site_description:
        parts.append(f"\n> {config.site_description}\n")
    for page in _pages:
        # canonical_url is None when site_url is unset; fall back to the source path.
        source = page.canonical_url or page.file.src_uri
        text = page.file.content_string.strip()
        parts.append(f"\n<!-- source: {source} -->\n\n{text}\n")
    Path(config.site_dir, OUTPUT_FILE).write_text("".join(parts), encoding="utf-8")
