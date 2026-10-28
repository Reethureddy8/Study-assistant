# Prompt Design: Permissive vs Strict

Both prompts live in [`parishiksha/generation.py`](../parishiksha/generation.py).
The same retriever (Gemini embeddings, k=5) and model (Llama-3.3-70B, temperature 0)
were used for both runs, so the prompt is the only variable.

## The two prompts

| | Permissive (v1) | Strict (v2) |
|---|---|---|
| Source of truth | "Answer using the context below" | "Answer ONLY using the context … no outside knowledge whatsoever" |
| Missing answer | Not specified | Reply with the exact string `I don't have that in my study materials.` |
| Citations | None | `[Source: wk10_XXXX]` after every factual claim, one id per bracket |

## Why each change matters

1. **An exact refusal string.** With no instruction for the "not in context" case,
   the model fills the gap from its own memory. A fixed string also makes refusals
   machine-checkable (`is_refusal()`), which the evaluation relies on.
2. **No outside knowledge.** This turns the context from a hint into a hard boundary.
3. **Enforced citation format.** Every claim points to a chunk id, so a wrong answer
   can be traced to retrieval or to generation in seconds. The code also flags
   cited ids that were never in the context (`Answer.unknown_citations`).

## Observed behaviour

**In scope: "What is Newton's second law of motion?"**
Both prompts gave the correct textbook definition. Only the strict one cited its
source (`wk10_0058`, section 6.5).

**In scope: "How do you calculate average speed?"**
The permissive answer was correct but padded with an invented worked calculation.
The strict answer gave the single-sentence definition with `[Source: wk10_0005]`.

**Out of scope: "What is the speed of light in a vacuum?"**
This is the important one. The permissive prompt first said the context did not
cover it, then answered anyway "according to general scientific knowledge". The
model noticed the gap and filled it regardless. The strict prompt returned
exactly `I don't have that in my study materials.` with no citations.

## Takeaway

A permissive grounding prompt fails quietly: answers look sourced even when they
are not. The strict prompt makes the out-of-scope case explicit and auditable, and
across the 12-question evaluation it refused all 3 out-of-scope questions while
keeping 9/9 in-scope answers grounded.
