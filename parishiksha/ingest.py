"""Turn NCERT chapter PDFs into labelled, cleaned page sections."""

from __future__ import annotations

import re
from dataclasses import dataclass
from pathlib import Path
from typing import Iterable

CONTENT_TYPES = ("concept", "worked_example", "activity", "end_of_chapter")

_WORKED_EXAMPLE = re.compile(r"example\s+\d+[.:]|answer\s*:")
_END_OF_CHAPTER = re.compile(r"revise,\s*reflect|pause and ponder|journey beyond|at a glance")
_ACTIVITY = re.compile(r"activity\s+\d+[.:]")
_SECTION_HEADING = re.compile(r"\n(\d+\.\d+[.\d]*\s+[A-Z][^\n]{5,60})")

# Layout noise that the PDF text layer carries along with the real content.
# These are applied line by line *before* whitespace is collapsed, so a
# caption pattern can never swallow the rest of the page.
_LINE_NOISE = [
    re.compile(r"Chapter-\d+\.indd.*"),
    re.compile(r"\d*\s*Exploration\|Grade\s*9\s*\d*"),
    re.compile(r"Grade\s+\d+\s*Curiosity\s*Chapter\s*\d+"),
    re.compile(r"Fig\.?\s*\d+\.\d+[a-z]?\s*:?.*"),
    re.compile(r"Table\s+\d+\.\d+\s*:?.*"),
    re.compile(r"^\s*\d{1,3}\s*$"),  # bare page numbers
]


@dataclass
class Section:
    """One PDF page with its chapter, nearest section heading and content type."""

    chapter: str
    page: int
    section: str
    content_type: str
    text: str


def classify_content_type(text: str) -> str:
    """Label a page as worked_example, end_of_chapter, activity or concept.

    Order matters: a worked example inside an activity page is still kept
    whole, so the most specific label wins.
    """
    lowered = text.lower()
    if _WORKED_EXAMPLE.search(lowered):
        return "worked_example"
    if _END_OF_CHAPTER.search(lowered):
        return "end_of_chapter"
    if _ACTIVITY.search(lowered):
        return "activity"
    return "concept"


def clean_text(text: str) -> str:
    """Strip headers, captions and page numbers, then normalise whitespace."""
    lines = []
    for line in text.splitlines():
        for pattern in _LINE_NOISE:
            line = pattern.sub("", line)
        lines.append(line)
    return re.sub(r"\s+", " ", "\n".join(lines)).strip()


def extract_pages(pdf_path: Path) -> list[dict]:
    """Return ``[{"page": n, "text": ...}]`` for every page of a PDF."""
    import fitz  # PyMuPDF; imported lazily so the rest of the package works without it

    with fitz.open(pdf_path) as doc:
        return [
            {"page": number, "text": page.get_text().strip()}
            for number, page in enumerate(doc, start=1)
        ]


def split_into_sections(pages: Iterable[dict], chapter: str) -> list[Section]:
    """Attach the most recent section heading and a content type to each page."""
    sections = []
    current = "Introduction"
    for page in pages:
        heading = _SECTION_HEADING.search(page["text"])
        if heading:
            current = heading.group(1).strip()
        sections.append(Section(
            chapter=chapter,
            page=page["page"],
            section=current,
            content_type=classify_content_type(page["text"]),
            text=page["text"],
        ))
    return sections


def load_corpus(raw_dir: Path, chapters: dict) -> list[Section]:
    """Extract and label every configured chapter PDF found in ``raw_dir``."""
    sections: list[Section] = []
    for filename, title in chapters.items():
        pdf_path = raw_dir / filename
        if not pdf_path.exists():
            raise FileNotFoundError(
                f"{pdf_path} is missing. Download it from https://ncert.nic.in/textbook/pdf/{filename}"
            )
        sections.extend(split_into_sections(extract_pages(pdf_path), title))
    return sections
