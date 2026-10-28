"""Grounded answer generation with enforced citations and an exact refusal string."""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from typing import Callable, Sequence

from .config import SETTINGS, require_env
from .retrieval import RetrievedChunk, Retriever

REFUSAL = "I don't have that in my study materials."

STRICT_PROMPT = f"""You are a study assistant for Class 9 Science students at PariShiksha.
Answer ONLY using the context provided below. Do NOT use any outside knowledge whatsoever.
If the answer is not present in the context, reply EXACTLY with this phrase and nothing else:
{REFUSAL}

After every factual claim you MUST cite the source chunk using EXACTLY this format: [Source: wk10_XXXX]
Where wk10_XXXX is the chunk_id from the context header. For example: [Source: wk10_0042]
Do not use any other citation format. Do not combine multiple chunk_ids in one bracket.

Context:
{{context}}

Question: {{question}}
Answer:"""

# Kept for the permissive-vs-strict comparison in docs/prompt_design.md.
PERMISSIVE_PROMPT = """You are a study assistant for Class 9 Science students.
Answer the student's question using the context below.

Context:
{context}

Question: {question}
Answer:"""

_CITATION = re.compile(r"\[Source:\s*(wk10_\d+)\]")

LLM = Callable[[str], str]


@dataclass
class Answer:
    question: str
    text: str
    retrieved: list[RetrievedChunk]
    cited_ids: list[str] = field(default_factory=list)

    @property
    def refused(self) -> bool:
        return is_refusal(self.text)

    @property
    def unknown_citations(self) -> list[str]:
        """Cited ids that were not in the context, i.e. invented by the model."""
        known = {r.chunk_id for r in self.retrieved}
        return [cid for cid in self.cited_ids if cid not in known]

    @property
    def sources(self) -> list[str]:
        cited = set(self.cited_ids)
        return [r.chunk.section for r in self.retrieved if r.chunk_id in cited]


def format_context(chunks: Sequence[RetrievedChunk]) -> str:
    return "\n\n---\n\n".join(
        f"[{r.chunk_id} | {r.chunk.section}]\n{r.chunk.text}" for r in chunks
    )


def parse_citations(text: str) -> list[str]:
    """Return cited chunk ids in order of first appearance, without duplicates."""
    return list(dict.fromkeys(_CITATION.findall(text)))


def is_refusal(text: str) -> bool:
    return text.strip().rstrip(".").lower() == REFUSAL.rstrip(".").lower()


def drop_short_chunks(chunks: Sequence[RetrievedChunk], min_words: int = 50) -> list[RetrievedChunk]:
    """The Stage-5 'junk filter' experiment. Worked examples are always kept.

    It lowered the score (see docs/fix_memo.md), so it is off by default.
    """
    return [
        r for r in chunks
        if r.chunk.content_type == "worked_example" or r.chunk.word_count > min_words
    ]


def groq_llm(
    model: str = SETTINGS.llm_model,
    temperature: float = SETTINGS.temperature,
    max_tokens: int = SETTINGS.max_answer_tokens,
) -> LLM:
    from groq import Groq

    client = Groq(api_key=require_env("GROQ_API_KEY"))

    def complete(prompt: str) -> str:
        response = client.chat.completions.create(
            model=model,
            temperature=temperature,
            max_tokens=max_tokens,
            messages=[{"role": "user", "content": prompt}],
        )
        return (response.choices[0].message.content or "").strip()

    return complete


class StudyAssistant:
    def __init__(
        self,
        retriever: Retriever,
        llm: LLM | None = None,
        prompt: str = STRICT_PROMPT,
        k: int = SETTINGS.top_k,
        filter_short_chunks: bool = False,
    ):
        self.retriever = retriever
        self.llm = llm or groq_llm()
        self.prompt = prompt
        self.k = k
        self.filter_short_chunks = filter_short_chunks

    def ask(self, question: str) -> Answer:
        retrieved = self.retriever.retrieve(question, k=self.k)
        if self.filter_short_chunks:
            retrieved = drop_short_chunks(retrieved)
        if not retrieved:
            return Answer(question, REFUSAL, [])

        reply = self.llm(self.prompt.format(context=format_context(retrieved), question=question))
        return Answer(question, reply, retrieved, parse_citations(reply))
