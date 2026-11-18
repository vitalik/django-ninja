"""MkDocs hook: expose the docs to LLMs as plain Markdown (https://llmstxt.org).

For the pages in `nav` (in navigation order, `not_in_nav` pages left out) it writes:

- each page's Markdown at its source path, e.g. /guide/api.md
- /llms.txt: the notes from `NOTES_FILE`, then links to those per-page files
- /llms-full.txt: the same notes, then the full text of the `FULL_SECTIONS` pages,
  with a page index at the top

See https://github.com/vitalik/django-ninja/issues/1708
"""

from pathlib import Path
from typing import Any, Dict, List, Tuple

from mkdocs.config.defaults import MkDocsConfig
from mkdocs.structure.files import Files
from mkdocs.structure.nav import Navigation
from mkdocs.structure.pages import Page

INDEX_FILE = "llms.txt"
FULL_FILE = "llms-full.txt"
# Hand-written guidance for assistants, next to mkdocs.yml. It goes right after the
# summary, where llms.txt allows prose and lists but no headings.
NOTES_FILE = "llms-best-practices.md"
# Nav sections whose pages go into llms-full.txt (the reference docs). Every nav
# page is still linked from llms.txt.
FULL_SECTIONS = ("Guide",)

_pages: List[Page] = []


def on_nav(nav: Navigation, config: MkDocsConfig, files: Files, **kwargs: Any) -> None:
    # Replaced on every build, since `mkdocs serve` keeps this module loaded.
    # Skip nav pages excluded from the site (e.g. `draft_docs`).
    _pages[:] = [page for page in nav.pages if not page.file.inclusion.is_excluded()]


def on_post_build(config: MkDocsConfig, **kwargs: Any) -> None:
    site_dir = Path(config.site_dir)
    base_url = (config.site_url or "").rstrip("/")

    def url(path: str) -> str:
        return f"{base_url}/{path}" if base_url else path

    notes_file = Path(config.config_file_path).parent / NOTES_FILE
    head = f"# {config.site_name}\n"
    if config.site_description:
        head += f"\n> {config.site_description}\n"
    head += f"\n{notes_file.read_text(encoding='utf-8').strip()}\n"

    groups: Dict[str, List[str]] = {}
    full_pages: List[Tuple[str, str, str]] = []
    for page in _pages:
        src_uri = page.file.src_uri
        text = page.file.content_string.strip()
        # Served at its source path, so relative links and images still resolve.
        md_file = site_dir / src_uri
        md_file.parent.mkdir(parents=True, exist_ok=True)
        md_file.write_text(f"{text}\n", encoding="utf-8")

        # Title from the H1: page.title is HTML-escaped and unset on --dirty builds.
        first_line = text.split("\n", 1)[0]
        title = first_line[2:] if first_line.startswith("# ") else src_uri
        group = page.parent.title if page.parent else "Docs"
        groups.setdefault(group, []).append(f"- [{title}]({url(src_uri)})\n")
        if any(section.title in FULL_SECTIONS for section in page.ancestors):
            # canonical_url is None when site_url is unset; fall back to the source path.
            full_pages.append((title, page.canonical_url or src_uri, text))

    sections = " and ".join(FULL_SECTIONS)
    index = head + (
        "\nEach link below is one page as Markdown. "
        f"All {sections} pages in a single file: [{FULL_FILE}]({url(FULL_FILE)})\n"
    )
    for group, links in groups.items():
        index += f"\n## {group}\n\n" + "".join(links)
    (site_dir / INDEX_FILE).write_text(index, encoding="utf-8")

    full_head = head + f"\n## {sections} pages\n\n"
    toc = []
    bodies = []
    # 1-based line of the first `<!-- source -->` line, after the TOC and a blank line.
    line = full_head.count("\n") + len(full_pages) + 2
    for title, source, text in full_pages:
        body = f"\n<!-- source: {source} -->\n\n{text}\n"
        toc.append(f"- [{title}]({source}): line {line}\n")
        bodies.append(body)
        line += body.count("\n")
    content = full_head + "".join(toc) + "".join(bodies)
    (site_dir / FULL_FILE).write_text(content, encoding="utf-8")
