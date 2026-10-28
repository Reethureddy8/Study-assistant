# Retrieval Misses — Wk10

Three queries where top-1 retrieved chunk did **not** contain the answer.

---

## Miss 1 — Q1: "What is displacement?"

**Top-1 chunk:** `wk10_0023` | Section: 4.3 Kinematic Equations for Motion in a Straight Line | Similarity: 0.632

**Chunk preview:**
> Describing Motion Around Us 63 This is the displacement of the car from the origin in
> 6 seconds. You have found that the area enclosed by the velocity-time graph and the
> time axis for a desired time interval is equal to the displacement in that time interval.

**Diagnosis:** Embedding limitation — the word "displacement" appears heavily across
worked-example and kinematic chunks, so the query vector is pulled toward high-frequency
co-occurrence contexts (calculations, graphs) rather than the definitional chunk in
section 4.1.2 where displacement is formally introduced.

---

## Miss 2 — Q2: "What are the three kinematic equations of motion?"

**Top-1 chunk:** `wk10_0026` | Section: 4.3 Kinematic Equations for Motion in a Straight Line | Similarity: 0.720

**Chunk preview:**
> As learnt in the earlier section, the displacement s of the object during the time
> interval t is given by the area enclosed within OABD. Thus, s = area of OABD =
> area of the rectangle OACD + area of the triangle ABC...

**Diagnosis:** Chunking miss — the chunk contains the derivation of s = ut + ½at²
but not the final three equations listed together; the splitter broke the equation
list across chunk boundaries (wk10_0024, wk10_0026, wk10_0027) so no single
top-1 chunk holds all three equations as a complete answer.

---

## Miss 3 — Q5: "State Newton's first law of motion."

**Top-1 chunk:** `wk10_0047` | Section: 6.4 Newton's First Law of Motion | Similarity: 0.728

**Chunk preview:**
> series of thought experiments that if a body moves along a horizontal plane and all
> impediments to its motion are removed, it will continue to move indefinitely...
> Isaac Newton used the word 'inertia' to describe the tendency of objects to resist
> change in their state of rest or uniform motion.

**Diagnosis:** Bad retrieval ranking — the top-1 chunk covers Newton's background
and inertia but the formal law statement ("An object at rest remains at rest...") 
lives in a neighbouring chunk (wk10_0046 or wk10_0048) that ranked 3rd or 4th;
the section heading keyword match boosted the inertia chunk above the statement chunk.

---

## Summary

| Miss | Failure category | Fix direction |
|------|-----------------|---------------|
| Q1 — displacement definition | Embedding limitation | Metadata filter: restrict retrieval to section 4.1.x for definition queries |
| Q2 — kinematic equations | Chunking miss | Wider token window for equation-list sections (Stage 5 fix) |
| Q5 — Newton's first law statement | Bad retrieval ranking | Dense retrieval ranks context chunk above statement chunk; reranking would promote the right chunk |
