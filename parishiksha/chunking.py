"""Content-aware, token-budgeted chunking.

Rules
-----
* ``worked_example`` pages stay whole: a problem must never be separated
  from its solution.
* ``end_of_chapter`` pages are split into one chunk per numbered question.
* ``concept`` and ``activity`` pages are split with a token-aware recursive
  splitter (250 tokens, 40 overlap by default).
"""

from __future__ import annotations

import json
import re
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Callable, Iterable

from .config import SETTINGS
from .ingest import Section, clean_text

MIN_SECTION_WORDS = 20
MIN_QUESTION_WORDS = 15
MIN_PIECE_CHARS = 20
_QUESTION_START = re.compile(r"(?=\n?\d+\.\s+[A-Z])")

TokenCounter = Callable[[str], int]
Splitter = Callable[[str], list]


@dataclass
class Chunk:
    chunk_id: str
    source: str
    section: str
    content_type: str
    page: int
    text: str
    token_count: int

    @property
    def word_count(self) -> int:
        return len(self.text.split())


def tiktoken_counter(encoding: str = SETTINGS.tiktoken_encoding) -> TokenCounter:
    import tiktoken

    enc = tiktoken.get_encoding(encoding)
    return lambda text: len(enc.encode(text))


def recursive_splitter(
    chunk_tokens: int = SETTINGS.chunk_tokens,
    overlap: int = SETTINGS.chunk_overlap,
    encoding: str = SETTINGS.tiktoken_encoding,
) -> Splitter:
    from langchain_text_splitters import RecursiveCharacterTextSplitter

    splitter = RecursiveCharacterTextSplitter.from_tiktoken_encoder(
        encoding_name=encoding, chunk_size=chunk_tokens, chunk_overlap=overlap
    )
    return splitter.split_text


def build_chunks(
    sections: Iterable[Section],
    count_tokens: TokenCounter | None = None,
    split: Splitter | None = None,
) -> list[Chunk]:
    """Chunk labelled sections. Tokenizer and splitter are injectable for tests."""
    count_tokens = count_tokens or tiktoken_counter()
    split = split or recursive_splitter()

    chunks: list[Chunk] = []

    def add(section: Section, text: str) -> None:
        chunks.append(Chunk(
            chunk_id=f"wk10_{len(chunks):04d}",
            source=section.chapter,
            section=section.section,
            content_type=section.content_type,
            page=section.page,
            text=text,
            token_count=count_tokens(text),
        ))

    for section in sections:
        text = clean_text(section.text)
        if len(text.split()) < MIN_SECTION_WORDS:
            continue

        if section.content_type == "worked_example":
            add(section, text)
        elif section.content_type == "end_of_chapter":
            for question in _QUESTION_START.split(text):
                question = question.strip()
                if len(question.split()) > MIN_QUESTION_WORDS:
                    add(section, question)
        else:
            for piece in split(text):
                piece = piece.strip()
                if len(piece) > MIN_PIECE_CHARS:
                    add(section, piece)

    return chunks


def save_chunks(chunks: Iterable[Chunk], path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    payload = [asdict(c) for c in chunks]
    path.write_text(json.dumps(payload, indent=2, ensure_ascii=False), encoding="utf-8")


def load_chunks(path: Path = SETTINGS.chunks_path) -> list[Chunk]:
    data = json.loads(path.read_text(encoding="utf-8"))
    return [Chunk(**item) for item in data]
