# Reflection Questionnaire — Wk10 Study Assistant v2.0

## Part A — Implementation specifics

### A1. Chunking decisions, with evidence

**Parameters:** chunk_size=250 tokens (tiktoken cl100k_base), overlap=50 tokens,
content_type via regex: `example \d+[.:]` → worked_example, `activity \d+[.:]`
→ activity, `revise, reflect|pause and ponder` → end_of_chapter, else → concept.

**Three chunks:**
- wk10_0063 | worked_example — page contained "Example 6.3:" triggering the regex;
  kept whole so the cricket-ball problem and its answer stay in one chunk.
- wk10_0026 | concept — kinematic section page, no example/activity markers;
  split at 250-token boundary mid-derivation.
- wk10_0008 | concept — average acceleration definition page; classified correctly,
  single page fit under token limit so kept whole.

### A2. The chunk that surprised me

wk10_0034 — classified as concept, 31 words:
"is a straight line indicating that the velocity changes with constant acceleration.
The slope of the graph gives the acceleration. Grade 8 Ganita Prakash..."
Expected: filtered out as noise at index time.
Got: passed the >30 word filter and entered the BM25 index, polluting retrieval
for kinematic queries. The heuristic caught genuine short fragments elsewhere but
missed this one because it technically contains physics vocabulary.

### A3. Loader choice

Stayed on PyMuPDF from Wk9. Tested by searching wk10_chunks.json for table-containing
pages in Chapter 6. The Newton's law examples were extracted as continuous prose —
no mid-row splits observed on these two chapters. Tables with numeric columns (e.g.,
velocity-time data) did flatten, but none of those were retrieval targets in my eval
set. OpenDataLoader-PDF would matter if the eval included table-specific queries.

---

## Part B — Numbers from your evaluation

### B1. Eval scores, raw

Out of 9 answered questions (excluding OOS):
- Correct: 8/9
- Partial: 1/9
- Grounded: 9/9
- OOS refused: 3/3

The number that bothered me most: 1 partial (Q7). Not because of the score but
because diagnosing it revealed a corpus gap — the F = Δp/Δt reasoning for the
fielder example does not exist in Chapter 4 or 6 as a retrievable chunk. The
system gave the best answer it could from what it had. That is a content problem,
not an engineering problem, and those are harder to fix.

### B2. The single worst question

**Question:** "Why does a fielder pull hands back while catching a fast cricket ball?"

**System answer:** "A fielder pulls their hands back while catching a fast cricket
ball to minimize the impact and injury to their hands, as applying a smaller force
to the moving ball also minimises injury to the fielder [Source: wk10_0063]."

**Top-3 retrieved:** wk10_0063, wk10_0062, wk10_0065

**Failure mode:** mixed_structure — the worked_example chunk held the conclusion
but the force-time mechanism (F = Δp/Δt) was absent from the corpus entirely.
The model answered faithfully from incomplete source material.

### B3. Before-and-after on fix

Fix: junk filter — drop non-worked_example chunks under 50 words from retrieved
context before passing to model.

| Metric | v1 | v2 | Delta |
|--------|----|----|-------|
| Correct | 8/9 | 7/9 | -1 |
| Grounded | 9/9 | 8/9 | -1 |
| OOS refused | 3/3 | 3/3 | 0 |

The fix made things worse. Q1 regressed because the filter removed wk10_0015,
a chunk that carried enough definitional signal for the model to answer
"What is displacement?" correctly. Without it, the model over-refused.
A negative delta is still a valid result — it tells me the filter threshold
was wrong and the real fix for Q1 is a metadata-based section filter, not
a word-count gate.

---

## Part C — Debugging stories

### C1. The retrieved chunk that fooled me

**Query:** "What is displacement?"
**Top-1:** wk10_0023 | similarity: 0.632
**Chunk preview:** "Describing Motion Around Us 63 This is the displacement of
the car from the origin in 6 seconds. You have found that the area enclosed by
the velocity-time graph..."

Ranked top-1 because "displacement" appears 4 times in a kinematic calculation
context — high co-occurrence with the query term. But the chunk contains a
worked calculation, not the definition. The definition lives in section 4.1.2
but its embedding is diluted by surrounding prose about distance vs displacement
comparisons, so it ranked 4th.

### C2. The bug that took longest

The chunk_id format mismatch. The dense retriever (Chroma) stored IDs as
"wk10_0063" but the raw chunks list used integers (63). When I tried to look up
a chunk by ID to diagnose a miss, `next((c for c in chunks if c["chunk_id"] == "wk10_0063"))`
returned nothing. Took 20 minutes to realise the two systems had different ID
formats because both worked fine independently — the bug only surfaced at the
diagnosis step. Fix: always use the same ID format end-to-end; assign string IDs
at chunk creation time, not at embedding time.

### C3. The thing that still bothers me

Q1 — "What is displacement?" — refused in v2 and answered correctly but
incompletely in v1. The definition chunk (section 4.1.2) exists but never
ranks top-1 because the embedding model associates "displacement" more strongly
with kinematic calculation contexts than with the definitional sentence. In Wk11
I would add a content_type=definition chunk type for formally introduced terms,
and filter retrieval to that type for "what is X" query patterns.

---

## Part D — Architecture and tradeoffs

### D1. Why hybrid retrieval (or why not)?

In my eval, Q9 — "What decides how far a car travels after brakes are applied?"
— retrieved wk10_0027 correctly with dense (similarity 0.644). But Q2 —
"What are the three kinematic equations of motion?" — dense returned the
derivation chunk (wk10_0026) while BM25 returned chunk 33 (the intro) at rank 1.
Neither was perfect. For exact-term queries like "v = u + at", BM25 would win
trivially. For paraphrased queries like Q9, dense wins. A hybrid fusing both
would handle both cases. At student scale the engineering cost is low. At
50k queries/day the operational complexity of running two indices is real but
justified by the recall gain.

### D2. CRAG / Self-RAG

CRAG would have helped Q1 — the retriever returned a high-similarity but
wrong-type chunk (calculation instead of definition). A CRAG grader would
score that chunk low on relevance and trigger a query rewrite toward
"define displacement". For Q7 it would not have helped — the corpus gap
means a rewrite still returns nothing better. CRAG is worth building when
bad retrievals are common and rewritable. When the gap is in the source
content, CRAG just burns extra tokens on a retry that fails the same way.

### D3. Honest pilot readiness

No. Three things I'd verify first:
1. Q1 refusal in v2 — the displacement definition fails to retrieve reliably.
   A student asking "what is displacement" getting "I don't have that" on a
   chapter about motion is a trust-destroying failure.
2. Chunk_id format consistency — the mismatch between raw chunks (int) and
   Chroma (string wk10_XXXX) means citation debugging is broken in production.
   This needs to be a single source of truth before any demo.
3. The corpus covers only 2 chapters. The teacher tested 30 questions across
   more content. Without expanding corpus coverage, out-of-scope refusals
   will dominate and erode teacher confidence faster than wrong answers would.

---

## Part E — Effort and self-assessment

### E1. Effort rating

7/10. The debugging loop around chunk_id format and the Q7 corpus gap
investigation consumed time I had planned for polishing the eval set.
Genuinely proud of: writing the fix_memo honestly when the fix made
things worse. It would have been easy to cherry-pick a question where
the fix helped and call it done.

### E2. The gap between me and a stronger student

A stronger student would have caught the chunk_id format mismatch on Day 1
by printing both formats side by side during the embedding step. I only
found it during Stage 5 diagnosis. The lesson: always verify that IDs
round-trip correctly between your chunker, vector store, and retriever
before building anything on top.

### E3. Industry Pointer I'd explore in 6 months

**Eval-driven development** (Section 9). My Wk10 eval set was hand-built
and biased toward questions I expected the system to answer. A production
team adds a question every time a real user surfaces a failure. The eval
set grows with the system. My first concrete step: instrument ask() to log
every query and response to a CSV, then weekly review the worst-scoring
responses and add them to the eval set. The eval becomes the moat.

### E4. Two more days

First: fix the chunk_id format consistency end-to-end and add a
content_type=definition pass for section-opening sentences, then re-run
the full eval — this addresses the Q1 refusal which is the most
user-visible failure.

Last: expand the corpus to 2 more NCERT chapters and re-run the OOS eval
to check that refusal rate holds as in-scope content grows. Corpus
coverage is the thing that determines whether the teacher trusts the
system in a real demo, and right now 2 chapters is too narrow to ship.
