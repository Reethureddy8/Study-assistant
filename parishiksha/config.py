"""Central configuration: paths, model names and retrieval defaults.

Every value can be overridden with an environment variable so experiments
don't require code edits.
"""

from __future__ import annotations

import os
from dataclasses import dataclass, field
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent


def _env(name: str, default: str) -> str:
    return os.getenv(name, default)


@dataclass(frozen=True)
class Settings:
    # Data locations
    raw_dir: Path = PROJECT_ROOT / "data" / "raw"
    processed_dir: Path = PROJECT_ROOT / "data" / "processed"
    evaluation_dir: Path = PROJECT_ROOT / "evaluation"
    chroma_dir: Path = Path(_env("PARISHIKSHA_CHROMA_DIR", str(PROJECT_ROOT / "chroma_store")))

    # Source chapters: PDF file name -> human-readable chapter title
    chapters: dict = field(default_factory=lambda: {
        "iesc104.pdf": "Chapter 4 - Describing Motion Around Us",
        "iesc106.pdf": "Chapter 6 - How Forces Affect Motion",
    })

    # Chunking
    chunk_tokens: int = 250
    chunk_overlap: int = 40
    tiktoken_encoding: str = "cl100k_base"

    # Models
    llm_model: str = _env("PARISHIKSHA_LLM_MODEL", "llama-3.3-70b-versatile")
    embed_model: str = _env("PARISHIKSHA_EMBED_MODEL", "gemini-embedding-001")
    collection_name: str = "parishiksha_chunks"

    # Retrieval / generation
    top_k: int = 5
    temperature: float = 0.0
    max_answer_tokens: int = 512

    @property
    def chunks_path(self) -> Path:
        return self.processed_dir / "wk10_chunks.json"


SETTINGS = Settings()


def load_env() -> None:
    """Load a local .env file if python-dotenv is installed."""
    try:
        from dotenv import load_dotenv
    except ImportError:
        return
    load_dotenv(PROJECT_ROOT / ".env")


def require_env(name: str) -> str:
    """Return an API key from the environment or fail with a helpful message."""
    load_env()
    value = os.getenv(name)
    if not value:
        raise RuntimeError(
            f"{name} is not set. Copy .env.example to .env and add your key."
        )
    return value
