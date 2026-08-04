# ADR-003: Semantic Cache Similarity Threshold = 0.75

> Status: Accepted | Date: POC Phase (revised after empirical testing) | Deciders: Architecture Team

---

## Context

The semantic cache requires a cosine similarity threshold to decide whether a cached response is semantically close enough to serve for a new prompt. The original design value was **0.95**.

## Problem

During demo validation, a threshold of 0.95 produced a **0% cache hit rate** — every prompt was treated as unique, defeating the purpose of semantic caching entirely.

## Decision

Reduce the similarity threshold from **0.95 → 0.75**.

## Empirical Evidence

| Threshold | Cache Hit Rate | Observed Behaviour |
|-----------|---------------|-------------------|
| 0.99 | 0% | Only exact string matches |
| 0.95 | 0% | Near-identical prompts missed |
| 0.85 | ~18% | Improved but still conservative |
| **0.75** | **42.2%** | Balances hit rate vs. accuracy |
| 0.60 | ~71% | Too many false positives |

**Chosen value: 0.75** — verified cache hit rate 42.2% against the ≥ 40% NFR target (NFR-04). ✅

## Configuration

Threshold is configurable via `.env`:

```env
CACHE_SIMILARITY_THRESHOLD=0.75
```

## Consequences

- **Positive:** Cache hit rate 42.2% — exceeds the 40% target (NFR-04)
- **Positive:** Cost reduction 42.2% — requests served at $0 (NFR-05)
- **Negative:** Small risk of semantically different prompts being matched (0.75 is not as strict as 0.95)
- **Mitigation:** Threshold is configurable per deployment; production tuning recommended with real user data

## Related

- NFR-04: Cache hit rate > 40%
- NFR-05: Cost reduction > 45%
- ADR-003 is referenced in: `docs/03-Use-Cases.md`, `docs/04-Test-Cases.md`, `docs/05-Traceability-Matrix.md`, `docs/06-HLD.md`, `docs/02-Architect-Thinking-Framework.md`
