from parishiksha.chunking import build_chunks, load_chunks, save_chunks
from parishiksha.config import SETTINGS
from parishiksha.ingest import Section

WORDS = " ".join(f"word{i}" for i in range(40))


def count_words(text):
    return len(text.split())


def halve(text):
    words = text.split()
    mid = len(words) // 2
    return [" ".join(words[:mid]), " ".join(words[mid:])]


def make(content_type, text):
    return Section("Ch4", 3, "4.1 Speed", content_type, text)


def test_worked_example_is_never_split():
    chunks = build_chunks([make("worked_example", WORDS)], count_words, halve)
    assert len(chunks) == 1
    assert chunks[0].token_count == 40


def test_concept_pages_use_the_splitter():
    chunks = build_chunks([make("concept", WORDS)], count_words, halve)
    assert len(chunks) == 2
    assert [c.chunk_id for c in chunks] == ["wk10_0000", "wk10_0001"]


def test_end_of_chapter_splits_per_question():
    q = " ".join(["because"] * 20)
    text = f"1. What is speed {q} 2. Define velocity {q}"
    chunks = build_chunks([make("end_of_chapter", text)], count_words, halve)
    assert len(chunks) == 2
    assert chunks[1].text.startswith("2. Define velocity")


def test_tiny_pages_are_dropped():
    assert build_chunks([make("concept", "too short")], count_words, halve) == []


def test_save_and_load_round_trip(tmp_path):
    chunks = build_chunks([make("worked_example", WORDS)], count_words, halve)
    path = tmp_path / "chunks.json"
    save_chunks(chunks, path)
    assert load_chunks(path) == chunks


def test_shipped_chunk_file_loads():
    chunks = load_chunks(SETTINGS.chunks_path)
    assert len(chunks) == 81
    assert len({c.chunk_id for c in chunks}) == len(chunks)
