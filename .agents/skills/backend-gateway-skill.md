# Skill: Backend Gateway

## Identity
- **Skill ID**: `backend-gateway-skill`
- **Domain**: Python / FastAPI — Gateway, Routing, Cache, Queue, Providers
- **Used By**: Implementation Agent, Testing Agent, Architecture Review Agent

---

## Purpose

Provides implementation-level knowledge of every backend module in `src/` so agents
can generate correct, idiomatic, and boundary-respecting code for the LLM Gateway.

---

## Technology Stack

| Layer | Choice | Rationale |
|-------|--------|-----------|
| API Framework | Python FastAPI | Async-native, OpenAPI auto-docs, header parsing |
| ASGI Server | Uvicorn | Production-grade async server |
| Semantic Cache | Pure-Python cosine similarity (POC) → Qdrant/Pinecone (prod) | No external deps for demo |
| Rate Limiting | In-memory token bucket (POC) → Redis (prod) | Avoids Redis dep in demo |
| Analytics Store | `data/analytics.json` (POC) → TimescaleDB (prod) | File-based for demo speed |
| Auth | API key + JWT; brute-force lockout after 10 failures → 5 min lock | `src/api/middleware/auth.py` |
| Provider Sim | Python classes mimicking OpenAI / Anthropic / Google SDKs | No real API keys needed |

---

## Module Reference

### `src/api/main.py` — App Factory
- Creates the FastAPI application instance
- Registers middleware: auth, rate limiter, CORS
- Mounts routers: `/api/v1/`
- **No emoji** in logging (Windows cp1252 compatibility)
- Must not import runtime services at module level (avoid circular imports)

### `src/api/routes/route.py` — Gateway Endpoint
```
POST /api/v1/route
Headers: Authorization, X-NFR-Latency, X-NFR-Cost, X-NFR-Accuracy,
         X-Model-Preference, X-Context-Window, X-Stream-Required
Body:    { "messages": [...], "stream": false }
```
Response includes `metadata` block:
```json
{
  "metadata": {
    "cache_hit": false,
    "latency_ms": 1234,
    "cost": 0.002,
    "failover_count": 0,
    "selected_reason": "nfr_match"
  }
}
```

### `src/api/middleware/auth.py` — Authentication
- Validates `Authorization: Bearer {api_key}` header
- Tracks failed attempts per IP; locks out after 10 failures for 5 minutes
- Returns `401` on invalid key, `429` on lockout
- **Do not** store raw API keys — store `api_key_hash`

### `src/api/middleware/rate_limit.py` — Rate Limiting
- Token bucket algorithm per `user_id` + time window
- Tier quotas enforced (Free: 10 req/min, Basic: 100, Pro: 500, Enterprise: 5000)
- Returns `429` with `Retry-After` header when bucket empty
- POC: in-memory dict; production: Redis `ratelimit:{user_id}:{window}`

---

### `src/gateway/nfr_parser.py` — NFR Parser
Parses and validates custom HTTP headers:
```python
def parse_nfr_headers(headers: dict) -> NFRConfig:
    latency  = headers.get("x-nfr-latency", "medium")   # low|medium|high
    cost     = headers.get("x-nfr-cost", "medium")       # low|medium|high
    accuracy = headers.get("x-nfr-accuracy", "standard") # standard|high|critical
    ...
```
- Returns a typed `NFRConfig` dataclass (or Pydantic model)
- Raises `400` on invalid header values
- Parsing must complete in < 5 ms

### `src/gateway/model_selector.py` — Model Selector
```python
def select_model(nfr: NFRConfig, available_models: list[Model]) -> Model:
    score = (latency_score * 0.30) + (cost_score * 0.40) + (accuracy_score * 0.30)
    ...
```
- Scoring weights: Cost 40%, Latency 30%, Accuracy 30%
- Returns ranked list; first available model wins
- Must not call provider APIs — selection is pure scoring logic

### `src/gateway/failover.py` — Failover & Circuit Breaker
```python
class CircuitBreaker:
    CLOSED     → normal operation
    OPEN       → fail fast (opens after 5 failures)
    HALF_OPEN  → probe with 3 requests after 60 s timeout
```
Failover levels executed in order:
1. Same model, different provider
2. Same model, different region
3. Different model, same family
4. Different model, different family

- Each level uses exponential backoff
- Circuit breaker state per provider
- Failover must complete in < 500 ms total

### `src/gateway/router.py` — Main Orchestrator
Request flow:
```
receive request
    → parse NFR headers      (nfr_parser)
    → check semantic cache   (semantic_cache)  ← return early if hit
    → select model           (model_selector)
    → dispatch to provider   (provider registry)
    → on failure → failover  (failover)
    → emit analytics event   (analytics collector)
    → return response + metadata
```
- Every path through `router.py` must emit an analytics event
- Cache hit path must still emit analytics with `cache_hit: true`

---

### `src/cache/semantic_cache.py` — Semantic Cache
```python
SIMILARITY_THRESHOLD = float(os.getenv("CACHE_SIMILARITY_THRESHOLD", "0.75"))

def get(prompt: str) -> CacheEntry | None:
    embedding = embed(prompt)
    for entry in store:
        if cosine_similarity(embedding, entry.embedding) >= SIMILARITY_THRESHOLD:
            return entry
    return None

def set(prompt: str, response: str, model: str) -> None:
    ...
```
- Threshold is configurable via `.env` — never hardcode
- L1: in-memory dict keyed by prompt hash (TTL 24 h)
- L2: vector store (Qdrant / Pinecone in production)
- Cache lookup must be < 50 ms

---

### `src/providers/registry.py` — Provider Registry
- Central catalog of all models: name, provider, family, cost/token, latency rating
- `get_provider(model_name, region)` returns provider instance
- `get_failover_chain(model_name)` returns ordered fallback list
- New providers must implement `BaseProvider` interface:
```python
class BaseProvider(ABC):
    @abstractmethod
    async def complete(self, messages: list, **kwargs) -> ProviderResponse: ...

    @abstractmethod
    def estimate_cost(self, prompt_tokens: int, completion_tokens: int) -> float: ...
```

### `src/providers/{openai,anthropic,google}_simulator.py` — Simulators
- Mimic real provider SDK behaviour
- Configurable failure rate via `FAILURE_RATE` env var (default `0.0`)
- Return realistic latency distributions
- **Never** make real HTTP calls to LLM provider APIs

---

### `src/analytics/collector.py` — Analytics Collector
```python
def record(event: AnalyticsEvent) -> None:
    # appends to data/analytics.json in POC
    # writes to TimescaleDB in production
```
`AnalyticsEvent` fields:
- `timestamp`, `request_id`, `user_id`, `tier`
- `model_selected`, `provider`, `region`
- `cache_hit`, `failover_count`, `failover_levels`
- `prompt_tokens`, `completion_tokens`, `cost_usd`
- `latency_ms`, `nfr_latency`, `nfr_cost`, `nfr_accuracy`
- `status` (`success` / `error`)

---

## Code Generation Rules

1. All new modules must have a module-level docstring explaining purpose and boundaries
2. All public functions must have type annotations
3. Configuration values (thresholds, timeouts, weights) must be read from `os.getenv()`
4. No hardcoded API keys, secrets, or provider URLs
5. New providers must subclass `BaseProvider` — no standalone classes
6. All async functions must be `async def` — no `asyncio.run()` inside route handlers
7. Error responses must follow the existing format: `{"detail": "...", "code": "..."}`
8. Windows compatibility: no emoji in log strings; use `logging` not `print()`
9. Do not add new database tables without a corresponding migration file
10. Do not modify `data/analytics.json` schema without updating `AnalyticsEvent`

---

## Performance Constraints (Must Be Met)

| Operation | Budget |
|-----------|--------|
| NFR header parsing | < 5 ms |
| Cache lookup (L1) | < 10 ms |
| Cache lookup (L2 vector) | < 50 ms |
| Model selection scoring | < 5 ms |
| Full request (cache hit) | P95 < 500 ms |
| Full request (cache miss) | P95 < 2,000 ms |
| Failover completion | < 500 ms |

---

## Security Rules (Must Enforce in Generated Code)

- Never log full API keys — log only last 4 characters
- Input validation on all request bodies (Pydantic models)
- XSS protection on any string returned to frontend
- All provider errors must be caught and mapped — never propagate raw provider errors
- Auth failures must increment brute-force counter before returning `401`
