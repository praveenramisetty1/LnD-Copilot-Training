# ADR-008: Model Selection Scoring Weights — Cost 40%, Latency 30%, Accuracy 30%

> Status: Accepted | Date: Architecture Phase | Deciders: Architecture Team

---

## Context

The model selector must score available LLM models against declared NFR requirements and select the optimal model. A weighted scoring algorithm was chosen over rule-based selection. The weights determine how much each NFR dimension influences the final model score.

## Decision

**Scoring weights: Cost 40% · Latency 30% · Accuracy 30%**

```python
# src/gateway/model_selector.py
WEIGHTS = {
    "cost":     0.40,
    "latency":  0.30,
    "accuracy": 0.30,
}

def score_model(model, nfr):
    return (
        WEIGHTS["cost"]     * cost_score(model, nfr.cost) +
        WEIGHTS["latency"]  * latency_score(model, nfr.latency) +
        WEIGHTS["accuracy"] * accuracy_score(model, nfr.accuracy)
    )
```

## Rationale

### Why Cost is Primary (40%)

Cost reduction is the **primary business driver** for an LLM gateway. Without meaningful cost optimisation, there is no compelling reason to add middleware. The gateway must demonstrably reduce LLM spend.

### Why Latency and Accuracy are Equal (30% each)

- Latency and accuracy represent a classic trade-off in LLM selection (faster models are typically less accurate)
- Equal weighting reflects that neither is universally more important — the NFR headers allow consumers to express their own preference
- The header values (`low/medium/high`) modulate the effective score for each dimension per request

### Alternatives Considered

| Weight Set | Rationale | Rejected Because |
|------------|-----------|-----------------|
| Equal (33/33/33) | No business priority | Ignores cost-as-primary-driver |
| Cost 60%, Lat 20%, Acc 20% | Aggressive cost focus | Over-penalises accuracy-critical use cases |
| **Cost 40%, Lat 30%, Acc 30%** | Balanced with cost priority | **Chosen** |
| Lat 50%, Cost 30%, Acc 20% | Latency-first | Wrong for most enterprise use cases |

## NFR Score Mapping

| NFR Value | Score Applied |
|-----------|--------------|
| `low` | 1.0 (best for cost/latency; worst for accuracy) |
| `medium` | 0.6 |
| `high` | 0.2 (worst for cost/latency; best for accuracy) |
| `critical` | 0.0 (accuracy only) |

## Consequences

- **Positive:** Cost savings verified at 42.2% of requests served from cache at $0
- **Positive:** Model selection correctly routes low-cost NFRs to GPT-3.5-Turbo / Claude Haiku
- **Positive:** High-accuracy NFRs correctly route to GPT-4 / Claude Opus
- **Negative:** Fixed weights may not suit all consumer profiles
- **Mitigation:** Weights are configurable via `.env` for production tuning

## Related

- FR-01: NFR-based model auto-selection
- ADR-009: Circuit breaker thresholds
- `docs/03-Use-Cases.md`: UC-01
