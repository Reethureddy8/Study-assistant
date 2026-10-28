# Fix Memo — Stage 5

## Target failure
**Q7:** "Why does a fielder pull hands back while catching a fast cricket ball?"
- v1 score: correctness=partial, grounded=yes
- Failure-mode catalog: `mixed_structure`

## Diagnosis
The worked_example chunk (wk10_0063) held the surface conclusion — "pulling back
reduces injury" — but the force-time mechanism (F = Δp/Δt, larger Δt → smaller F)
was absent from the top-5 retrieved chunks. Initial hypothesis: neighbouring chunk
ranked 6th, outside k=5 window.

## Fix attempted
**Junk filter**: drop any non-worked_example chunk under 50 words before passing
context to the model. Target: remove chunk 34 (31-word graph label artifact) and
11 other noise fragments that were polluting BM25 scores and dense retrieval ranking.

## Score delta

| Metric | v1 (baseline) | v2 (fix) | Change |
|--------|--------------|----------|--------|
| Correct | 8/9 | 7/9 | **-1** |
| Partial | 1/9 | 1/9 | 0 |
| No/refused | 0/9 | 1/9 | **+1** (regression) |
| Grounded | 9/9 | 8/9 | **-1** |
| OOS refused | 3/3 | 3/3 | 0 |

## Honest assessment
The fix made things worse. Two problems:

**1. Q1 regression.** The filter dropped wk10_0015 (a position-time graph chunk,
55 words, ranked 5th for "What is displacement?"). That chunk contained enough
definitional signal that the model answered correctly in v1. Without it, the
remaining 4 chunks were all calculation/kinematic contexts and the model correctly
refused — but that refusal was wrong because the definition does exist in the corpus.
The filter was too aggressive.

**2. Q7 is a corpus gap, not a retrieval bug.** After exhaustive search, the
F = Δp/Δt mechanism for the fielder example does not appear in Chapter 4 or
Chapter 6 as a retrievable chunk. The only "time of contact" mention is in a
Chapter 6 end-of-chapter exercise (chunk 98), not an explanation. The model gave
the correct surface answer from what the corpus actually contains. Scoring it
"partial" is accurate but the fix direction (retrieval tuning) was wrong — the
missing reasoning is missing from the source PDF, not from retrieval.

## What the correct fix would be
- **Q7**: Add an explicit worked_example chunk that states the F = Δp/Δt reasoning.
  This requires either a richer source PDF or a manually authored chunk — not a
  retrieval or prompt change.
- **Q1**: The definition of displacement lives in section 4.1.2 but the embedding
  model pulls toward kinematic/calculation contexts. The real fix is a metadata
  filter: for queries containing "what is X" where X is a physics term, restrict
  retrieval to concept chunks in the relevant section. That is a Wk11 task.

## Single-variable discipline
The junk filter was a single variable change. The eval was re-run cleanly. The
result was negative. This is a valid experimental outcome — knowing a fix does not
work is as useful as knowing one that does.
