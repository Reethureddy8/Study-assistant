import pytest

from parishiksha.chunking import Chunk, load_chunks
from parishiksha.generation import REFUSAL, StudyAssistant, is_refusal, parse_citations
from parishiksha.retrieval import BM25Retriever, RetrievedChunk, tokenize


def chunk(cid, text, content_type="concept"):
    return Chunk(cid, "Ch6", "6.5 Second Law", content_type, 1, text, len(text.split()))


class FixedRetriever:
    def __init__(self, results):
        self.results = results

    def retrieve(self, query, k=5):
        return self.results[:k]


def test_tokenize_drops_punctuation():
    assert tokenize("F = ma, Newton's law!") == ["f", "ma", "newton", "s", "law"]


def test_bm25_boost_prefers_concept_over_question_page():
    text = "newton second law force acceleration"
    # BM25 needs the query terms to be rare in the corpus, so pad it with filler pages
    filler = [chunk(f"wk10_{i:04d}", f"friction opposes motion topic{i}") for i in range(2, 10)]
    chunks = [chunk("wk10_0000", text, "end_of_chapter"), chunk("wk10_0001", text, "concept"), *filler]
    top = BM25Retriever(chunks).retrieve("newton second law", k=1)[0]
    assert top.chunk_id == "wk10_0001"


def test_bm25_on_real_corpus_finds_newtons_laws():
    results = BM25Retriever(load_chunks()).retrieve("Newton's first law of motion inertia", k=5)
    assert any("Newton" in r.chunk.section for r in results)


def test_parse_citations_dedupes_in_order():
    text = "F = ma [Source: wk10_0062]. Unit is newton [Source: wk10_0063] [Source: wk10_0062]"
    assert parse_citations(text) == ["wk10_0062", "wk10_0063"]


@pytest.mark.parametrize("text", [REFUSAL, " i don't have that in my study materials "])
def test_refusal_detection(text):
    assert is_refusal(text)


def test_assistant_flags_invented_citations():
    retrieved = [RetrievedChunk(chunk("wk10_0001", "F = ma"), 0.9)]
    prompts = []

    def fake_llm(prompt):
        prompts.append(prompt)
        return "F = ma [Source: wk10_0001] [Source: wk10_0999]"

    answer = StudyAssistant(FixedRetriever(retrieved), llm=fake_llm).ask("Second law?")
    assert "[wk10_0001 | 6.5 Second Law]" in prompts[0]
    assert answer.cited_ids == ["wk10_0001", "wk10_0999"]
    assert answer.unknown_citations == ["wk10_0999"]
    assert answer.sources == ["6.5 Second Law"]
    assert not answer.refused


def test_assistant_refuses_without_calling_llm_when_nothing_retrieved():
    def fail(prompt):
        raise AssertionError("LLM should not be called")

    answer = StudyAssistant(FixedRetriever([]), llm=fail).ask("Photosynthesis?")
    assert answer.refused


def test_short_chunk_filter_keeps_worked_examples():
    retrieved = [RetrievedChunk(chunk("wk10_0001", "short", "worked_example"), 0.9),
                 RetrievedChunk(chunk("wk10_0002", "short"), 0.8)]
    answer = StudyAssistant(FixedRetriever(retrieved), llm=lambda p: REFUSAL,
                            filter_short_chunks=True).ask("q")
    assert [r.chunk_id for r in answer.retrieved] == ["wk10_0001"]
