# Skill: Frontend Dashboard

## Identity
- **Skill ID**: `frontend-dashboard-skill`
- **Domain**: React / TypeScript — Configuration UI & Analytics Dashboard
- **Used By**: Implementation Agent, Documentation Agent

---

## Purpose

Provides implementation-level knowledge for the two frontend surfaces of the LLM Gateway:
1. **Configuration UI** — manage routing rules, model catalog, user tiers, cache settings
2. **Analytics Dashboard** — real-time metrics, historical reports, conversational analytics

---

## Technology Stack

| Layer | Choice | Rationale |
|-------|--------|-----------|
| Framework | React 18+ | Component model, concurrent features |
| Language | TypeScript | Type safety across API contract boundary |
| UI Library | Material-UI (MUI) v5 | Consistent design system, accessible components |
| Charts | Recharts | Composable, React-native charting |
| State Management | Zustand | Lightweight; avoids Redux boilerplate for POC scope |
| API Client | Axios + React Query | Caching, retry, loading states |
| Build Tool | Vite | Fast HMR, ES module output |
| Linting | ESLint + Prettier | Enforced in CI |

---

## Application Structure

```
frontend/
├── src/
│   ├── api/              ← Axios client + React Query hooks
│   │   ├── client.ts     ← base Axios instance (reads VITE_API_URL from env)
│   │   ├── gateway.ts    ← /api/v1/route calls
│   │   └── analytics.ts  ← /api/v1/analytics/* calls
│   ├── components/
│   │   ├── common/       ← Button, Card, Table, Modal, StatusBadge
│   │   ├── config/       ← RoutingRuleBuilder, ModelCatalog, TierManager, CacheConfig
│   │   └── analytics/    ← MetricCard, LatencyChart, CostChart, CacheHitGauge,
│   │                        ProviderDistribution, ConversationalQuery
│   ├── pages/
│   │   ├── Dashboard.tsx         ← real-time metrics overview
│   │   ├── Configuration.tsx     ← routing rules + model catalog
│   │   ├── Users.tsx             ← user & tier management
│   │   ├── Analytics.tsx         ← historical reports + chat interface
│   │   └── ProviderHealth.tsx    ← live circuit breaker status
│   ├── store/
│   │   ├── configStore.ts        ← routing rules, model catalog (Zustand)
│   │   └── analyticsStore.ts     ← metrics, time range selection (Zustand)
│   ├── types/
│   │   ├── gateway.ts            ← NFRConfig, RouteRequest, RouteResponse, Metadata
│   │   ├── analytics.ts          ← AnalyticsEvent, MetricSummary, TimeSeriesPoint
│   │   └── config.ts             ← RoutingRule, ModelEntry, UserTier, CacheConfig
│   └── main.tsx
├── .env.example          ← VITE_API_URL, VITE_WS_URL
└── vite.config.ts
```

---

## Key Components

### Configuration UI

#### `RoutingRuleBuilder`
- Visual drag-and-drop rule editor
- Rule structure: `{ condition: NFRCondition, action: ModelAction, priority: number }`
- Validates that selected models exist in the model catalog
- Calls `PUT /api/v1/config/routing-rules` on save
- Must not call LLM provider APIs directly

#### `ModelCatalog`
- Displays all registered models: name, provider, family, cost/token, latency class
- Add / edit / disable models
- Calls `GET|POST|PATCH /api/v1/config/models`
- Disabling a model must warn if it is the primary for any routing rule

#### `TierManager`
- Displays tier quota table (Free / Basic / Pro / Enterprise)
- Edit quotas: req/min, req/day, tokens/day, queue priority
- Calls `PATCH /api/v1/config/tiers`

#### `CacheConfig`
- Edit `CACHE_SIMILARITY_THRESHOLD` (0.0–1.0 slider)
- Edit cache TTL (L1: 1–48 h; L2: 1–30 days)
- Manual cache flush button → `DELETE /api/v1/cache`
- Shows current cache size and estimated hit rate

---

### Analytics Dashboard

#### `MetricCard`
Props: `{ label, value, unit, trend, color }`
Displays: RPS, P95 latency (cached/uncached), cache hit %, cost/hour, error rate

#### `LatencyChart`
- Line chart: P50 / P95 / P99 latency over selected time window
- Data source: `GET /api/v1/analytics/latency?window=1h|24h|7d`
- Update interval: 5 s (real-time), 60 s (historical)

#### `CostChart`
- Stacked bar: cost per provider per day
- Overlaid line: cumulative cost reduction vs. no-cache baseline
- Target line at 45% cost reduction (visual reference)

#### `CacheHitGauge`
- Radial gauge showing current hit rate
- Green ≥ 40%, Amber 25–39%, Red < 25%
- Sub-label: "Target: > 40%"

#### `ProviderDistribution`
- Pie chart: request share by provider
- Drill-down: click provider → see model breakdown

#### `ConversationalQuery`
- Chat input: `"What was my total cost last month?"`
- Calls `POST /api/v1/analytics/query` with `{ question: string }`
- Renders response as text + optional embedded chart
- Shows loading skeleton during query (target: < 3 s response)

---

## API Contract (Frontend ↔ Backend)

All requests include:
```
Authorization: Bearer {api_key}
Content-Type: application/json
```

Key endpoints consumed by frontend:

| Method | Path | Purpose |
|--------|------|---------|
| `GET` | `/api/v1/analytics/summary` | Dashboard metric cards |
| `GET` | `/api/v1/analytics/latency` | Latency time-series |
| `GET` | `/api/v1/analytics/cost` | Cost per provider |
| `GET` | `/api/v1/analytics/cache` | Cache hit rate history |
| `POST` | `/api/v1/analytics/query` | NLU conversational query |
| `GET` | `/api/v1/config/routing-rules` | Load routing rules |
| `PUT` | `/api/v1/config/routing-rules` | Save routing rules |
| `GET` | `/api/v1/config/models` | Load model catalog |
| `POST` | `/api/v1/config/models` | Add model |
| `PATCH` | `/api/v1/config/models/:id` | Update model |
| `GET` | `/api/v1/providers/health` | Circuit breaker status |
| `DELETE` | `/api/v1/cache` | Flush cache |

---

## Code Generation Rules

1. All component props must have TypeScript interfaces — no `any`
2. API calls must go through `src/api/` layer — no `fetch()` in components
3. Environment variables accessed only via `import.meta.env.VITE_*`
4. No hardcoded API URLs, keys, or provider names in component code
5. All charts must be responsive (`<ResponsiveContainer>` wrapper)
6. Loading and error states required for every data-fetching component
7. Dashboard must load in < 3 s on initial render
8. Conversational query responses must appear in < 3 s
9. No direct calls to LLM provider APIs from the frontend — all through the gateway
10. Accessibility: all interactive elements must have ARIA labels

---

## Target UX Metrics

| Metric | Target |
|--------|--------|
| Dashboard initial load | < 3 s |
| Chart data refresh | < 1 s (real-time mode) |
| Conversational query response | < 3 s |
| Routing rule save round-trip | < 500 ms |
| NLU accuracy (conversational) | > 90% |
