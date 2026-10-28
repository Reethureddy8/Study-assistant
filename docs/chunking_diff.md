# Chunking Diff: Wk9 vs Wk10

## What changed

Wk9 used a word-based splitter (300 words, 50 word overlap) with a manual
words-per-token approximation (0.75 ratio). This meant chunk sizes were
estimated, not measured — a 300-word chunk could be anywhere from 250 to
400 tokens depending on scientific terminology density.

Wk10 switched to LangChain's `RecursiveCharacterTextSplitter.from_tiktoken_encoder`
(chunk_size=250 tokens, overlap=40 tokens) using the GPT-4 tokenizer. This
gives exact token counts at index time, which matters when the retriever and
the LLM context window are both token-budgeted. The total chunk count grew
from 101 (Wk9) to ~90 (Wk10) with tighter, more consistent sizes.
`worked_example` chunks are intentionally kept whole in both versions —
problem and solution must not be split.

## What the comparison revealed

On the query "What is displacement?", Wk9 returned a concept chunk from
Chapter 6 (Force) at Rank 1 — the wrong chapter entirely. Wk10 returned an
end_of_chapter chunk from Chapter 4 (Motion) at Rank 1, which is closer to
the right content area, though a direct concept chunk would be ideal. The
Rank 3 result (velocity-time graphs) was identical in both versions, showing
that BM25 keyword overlap still dominates for short queries regardless of
chunking strategy.

On "State Newton's second law of motion", both versions retrieved from the
correct section (6.5) but in different rank order. Wk10 surfaced the Newton's
Second Law activity chunk at Rank 1 vs Rank 2 in Wk9 — a small improvement.
The key difference is that token-aware sizing kept section-boundary chunks
more intact, reducing cases where a heading and its explanation landed in
separate chunks. Content-type filtering (keeping `worked_example` whole) means
the solution steps for Newton's law examples are never split from their setup —
the specific failure mode Wk9 was vulnerable to.
