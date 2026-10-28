# Failure Modes Document — PariShiksha Study Assistant

## Overview
This document identifies the top three production failure modes observed
during evaluation, grounded in actual eval results, not speculation.

---

## Failure Mode 1 — Retrieval Failure on High-Frequency Terms

**Observed in:** Q01 (displacement), Q02 (kinematic equations)

**What happens:** BM25, dense, and hybrid retrievers all fail to return
the correct definitional chunk for queries containing high-frequency
physics terms like "displacement", "velocity", "motion". These words
appear across 40+ chunks in our 71-chunk corpus, making them
non-discriminative for BM25. Dense retrieval also struggles because
all-MiniLM-L6-v2 was not fine-tuned on NCERT physics text.

**Production impact:** A student asking the most basic definitional
question — the most common first question — gets an incomplete or
wrong answer. In a pilot with 100 students, this affects the majority
of first interactions.

**Root cause from eval:** Q01 retrieved Page 23 (exercise page) instead
of Page 3 (definition page). The word "displacement" appears in
end-of-chapter questions, worked examples, and concept pages equally,
so no retriever can discriminate by keyword alone.

**Mitigation:** Fine-tune embedding model on NCERT QA pairs. Add
metadata filtering — prefer concept chunks for definition queries.

---

## Failure Mode 2 — Chunk Boundary Splits Equations from Context

**Observed in:** Q02 (kinematic equations incomplete)

**What happens:** The kinematic equations s = ut + ½at² appears in a
different chunk than the surrounding explanation. When the retriever
returns the explanation chunk but not the equation chunk, the LLM
produces an incomplete answer — listing only 2 of 3 equations.

**Production impact:** For a student preparing for exams, an incomplete
equation list is worse than no answer — they may memorize the wrong
set of equations and fail numerical problems.

**Root cause from eval:** Fixed-size chunking at 300 tokens split the
kinematic equations section across two chunks. The overlap of 50 tokens
was insufficient to keep the full equation set together.

**Mitigation:** Detect equation-dense pages and keep them whole.
Use semantic chunking that respects equation boundaries rather than
fixed token counts.

---

## Failure Mode 3 — Plausible-Looking Wrong Chunk Fools Grounding

**Observed in:** Q06 (Newton's second law retrieved from wrong section)

**What happens:** The retriever returns a chunk from "6.7 Forces Acting
on a System of Objects" for a query about Newton's second law. This
chunk mentions F=ma in passing but is primarily about system-level
force analysis. The LLM produces a partially correct answer — it gets
the law right but misses the F=ma formula derivation.

**Production impact:** This is the most dangerous failure mode for
production. The answer looks correct to a student but is missing
key detail. Unlike a wrong refusal (which the student notices),
a plausible incomplete answer is invisible — the student thinks
they understood when they did not.

**Root cause from eval:** BM25 matched on "Newton", "second", "law",
"force" — all present in the wrong chunk. The correct chunk (6.5)
was ranked second, not first.

**Mitigation:** Cross-encoder reranking (planned for Week 10) would
catch this — it reads query + chunk together and scores relevance
more accurately than BM25 or dense retrieval alone.

---

## Summary Table

| Failure Mode | Frequency | Severity | Mitigation |
|---|---|---|---|
| High-freq term retrieval failure | 2/13 questions | High | Fine-tune embeddings |
| Chunk boundary splits equations | 1/13 questions | High | Semantic chunking |
| Plausible wrong chunk | 1/13 questions | Critical | Cross-encoder reranking |

## Key Takeaway
All three failure modes are retrieval failures, not generation failures.
The LLM (Llama-3.1-8b) behaved correctly given what it received.
Improving the retriever is the highest-leverage intervention before
any production pilot.
