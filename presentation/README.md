# Presentation — LLM Gateway POC
**Propeller Technothon | Problem Statement 4**

---

## Slide Deck Outline

| # | Slide | Key Points |
|---|-------|-----------|
| 1 | **Title** | LLM Gateway Platform — Team name, date |
| 2 | **Problem Statement** | $30K/month waste, single-provider fragility, zero visibility |
| 3 | **Solution Overview** | 6 capabilities: NFR routing, cache, failover, queue, analytics, UI |
| 4 | **Architecture Diagram** | HLD from `docs/06-HLD.md` — component diagram |
| 5 | **NFR Routing Demo** | Screenshot: 2 requests, 2 different models, same prompt |
| 6 | **Semantic Cache Demo** | Screenshot: cache miss → hit, latency 800ms → 12ms |
| 7 | **Failover Demo** | Screenshot: OpenAI down → Anthropic used, failover_count=1 |
| 8 | **Analytics Dashboard** | Screenshot: summary metrics, provider distribution |
| 9 | **ROI & Business Value** | $144K–$216K annual saving, 99.95% availability |
| 10 | **Tech Stack** | FastAPI, Qdrant, Redis, TimescaleDB, React |
| 11 | **Test Coverage** | pytest results, coverage %, CI green badge |
| 12 | **Architecture Decisions** | 5 ADRs with rationale |
| 13 | **Future Scope** | Multi-region, A/B testing, fine-tuned model routing |
| 14 | **Q&A** | Refer to `demo/qna_prep.md` |

---

## Evidence Files (add to slides)
- Architecture diagram → `docs/06-HLD.md`
- Coverage report → `docs/evidence/coverage/`
- Load test results → `docs/evidence/load-test-results.png`
- ROI calculation → `docs/12-ROI-Business-Value.md`
- Evaluation mapping → `docs/00-Evaluation-Mapping.md`

---

## Presentation Tips
- Open Swagger UI during demo, not a pre-recorded video
- Show `metadata.selected_reason` and `metadata.nfr_score` in every response
- For failover demo: run circuit open/close live — it's reliable
- End with the analytics summary showing real numbers from the demo run
