# Evaluation Results — PariShiksha Study Assistant

## Corpus
- Chapter 4: Describing Motion Around Us (NCERT Class 9)
- Chapter 6: How Forces Affect Motion (NCERT Class 9)

## System Configuration
- Retriever: BM25 with content-type boosting
- Generator: Llama-3.1-8b-instant via Groq API
- Chunks: 71 (after cleaning), avg 225 words
- Top-k: 3 chunks per query
- Temperature: 0.0 (deterministic)

## Score Summary
| Metric | Score |
|--------|-------|
| Correct (direct + paraphrased) | 11/13 |
| Partial | 2/13 |
| Grounded | 13/13 |
| Refusals appropriate | 5/5 |

## Detailed Results

| Q | Question | Category | Correctness | Grounded | Refusal | Top Chunk Retrieved |
|---|----------|----------|-------------|----------|---------|---------------------|
| 1 | What is displacement? | direct | partial | yes | n/a | 4.4 Motion in a Plane |
| 2 | What are the three kinematic equations? | direct | partial | yes | n/a | 4.3 Kinematic Equations |
| 3 | What is uniform circular motion? | direct | yes | yes | n/a | 4.4 Motion in a Plane |
| 4 | What is average acceleration? | direct | yes | yes | n/a | 4.1.4 Average acceleration |
| 5 | State Newton's first law | direct | yes | yes | n/a | 6.4 Newton's First Law |
| 6 | State Newton's second law | direct | yes | yes | n/a | 6.5 Newton's Second Law |
| 7 | State Newton's third law | direct | yes | yes | n/a | 6.7 Forces on System |
| 8 | SI unit of force? | direct | yes | yes | n/a | 6.5 Newton's Second Law |
| 9 | What is friction and direction? | direct | yes | yes | n/a | 6.7 Forces on System |
| 10 | How to calculate average speed? | direct | yes | yes | n/a | 4.1.3 Average speed |
| 11 | Why fielder pulls hands back? | paraphrased | yes | yes | n/a | 6.5 Newton's Second Law |
| 12 | Circular motion — accelerating? | paraphrased | yes | yes | n/a | 4.4 Motion in a Plane |
| 13 | What decides braking distance? | paraphrased | yes | yes | n/a | 4.3 Kinematic Equations |
| 14 | What is photosynthesis? | out_of_scope | n/a | n/a | yes | — |
| 15 | Explain the water cycle | out_of_scope | n/a | n/a | yes | — |
| 16 | What is quantum entanglement? | out_of_scope | n/a | n/a | yes | — |
| 17 | Who is PM of India? | out_of_scope | n/a | n/a | yes | — |
| 18 | Newton's law of gravitation? | out_of_scope | n/a | n/a | yes | — |

## Failure Analysis

### Failure 1 — Q01: Wrong retrieval for displacement query
- **Query:** What is displacement?
- **Retrieved:** 4.4 Motion in a Plane (wrong)
- **Expected:** 4.1.2 Distance travelled and displacement
- **Cause:** BM25 matched on generic motion-related terms. The word "displacement" appears across many chunks, so BM25 could not discriminate. The correct chunk was ranked lower.

### Failure 2 — Q02: Incomplete kinematic equations
- **Query:** What are the three kinematic equations?
- **Retrieved:** Correct section but chunk was missing s = ut + ½at²
- **Cause:** The chunk boundary split the full equation list. The equation s = ut + ½at² appeared in a different chunk that was not retrieved in top-3.

## Working Examples
- Q05, Q06, Q07 — All three Newton's laws retrieved and answered correctly with proper grounding
- Q11 — Paraphrased real-world question (fielder catching ball) correctly mapped to Newton's second law context
- Q14-Q18 — All out-of-scope questions correctly refused, system did not hallucinate

## Key Observation
All 13 answered questions were grounded in retrieved context (13/13). The two failures were retrieval failures, not generation failures — confirming the expert hint that hallucination root cause is almost always upstream in the retriever.
