# Config UI Design — LLM Gateway Platform

> Status: Designed | Implementation: Partial / Future Scope
> Referenced by: docs/13-Premortem.md G01-B
> POC Status: Backend routing rule API designed; React frontend is production target

---

## Overview

The Configuration UI allows platform operators to manage routing rules, tier quotas, provider weights, and circuit breaker settings without restarting the gateway. Changes are applied at runtime via the Admin API.

---

## Architecture

```
┌─────────────────────────────────────────┐
│           React 18 + MUI v5             │
│  Config Dashboard (port 3000)           │
│                                         │
│  ┌──────────┐  ┌──────────┐  ┌───────┐ │
│  │ Routing  │  │ Provider │  │ Tier  │ │
│  │  Rules   │  │ Weights  │  │Quotas │ │
│  └──────────┘  └──────────┘  └───────┘ │
└─────────────────────────────────────────┘
                    │ REST
                    ▼
┌─────────────────────────────────────────┐
│        Admin API (FastAPI)              │
│  POST   /admin/routing-rules            │
│  PUT    /admin/routing-rules/{id}       │
│  DELETE /admin/routing-rules/{id}       │
│  GET    /admin/providers                │
│  PUT    /admin/providers/{id}/weight    │
│  GET    /admin/tiers                    │
│  PUT    /admin/tiers/{tier}/quota       │
│  POST   /admin/circuit-breaker/reset    │
└─────────────────────────────────────────┘
                    │
                    ▼
┌─────────────────────────────────────────┐
│     In-Memory Config Store (POC)        │
│     PostgreSQL config table (Prod)      │
└─────────────────────────────────────────┘
```

---

## React Component Tree

```
<App>
  <Sidebar>
    <NavItem icon="route" label="Routing Rules" />
    <NavItem icon="cloud" label="Providers" />
    <NavItem icon="people" label="Tier Quotas" />
    <NavItem icon="security" label="Circuit Breakers" />
  </Sidebar>
  <MainContent>
    <RoutingRulesPage>
      <RuleTable />          ← List all rules (priority, NFR match, model target)
      <AddRuleDialog />      ← Modal: create new routing rule
      <EditRuleDialog />     ← Modal: edit existing rule
    </RoutingRulesPage>
    <ProvidersPage>
      <ProviderCard />       ← Per provider: status, weight slider, latency
      <CircuitBreakerPanel/> ← State indicator + manual reset button
    </ProvidersPage>
    <TierQuotasPage>
      <TierTable />          ← req/min, req/day, tokens/day per tier
      <EditTierDialog />     ← Modal: update quota values
    </TierQuotasPage>
  </MainContent>
</App>
```

---

## Admin API Contract

### Routing Rules

| Method | Path | Description |
|--------|------|-------------|
| `GET` | `/admin/routing-rules` | List all routing rules ordered by priority |
| `POST` | `/admin/routing-rules` | Create a new routing rule |
| `PUT` | `/admin/routing-rules/{id}` | Update an existing rule |
| `DELETE` | `/admin/routing-rules/{id}` | Delete a rule |

**Routing Rule Schema:**
```json
{
  "id": "uuid",
  "priority": 10,
  "conditions": {
    "nfr_latency": "low",
    "nfr_cost": "low",
    "nfr_accuracy": "standard"
  },
  "target_model": "gpt-3.5-turbo",
  "fallback_models": ["claude-3-haiku", "gemini-pro"],
  "enabled": true
}
```

### Provider Management

| Method | Path | Description |
|--------|------|-------------|
| `GET` | `/admin/providers` | List all providers with status and weights |
| `PUT` | `/admin/providers/{id}/weight` | Update scoring weight for a provider |
| `POST` | `/admin/circuit-breaker/reset` | Manually reset a circuit breaker to CLOSED |

### Tier Quotas

| Method | Path | Description |
|--------|------|-------------|
| `GET` | `/admin/tiers` | List all tier quota configurations |
| `PUT` | `/admin/tiers/{tier}/quota` | Update quota values for a tier |

---

## POC Status

| Component | Status |
|-----------|--------|
| Admin API endpoints (backend) | 📅 Partial — structure designed, full CRUD implementation in progress |
| React Config Dashboard | 📅 Future Scope — production target (Path B only) |
| In-memory config store | ✅ Implemented — routing rules loaded from `.env` / config dict |
| Runtime rule update | 📅 Future Scope — requires API + persistence layer |

---

## Security

- Admin API protected by separate admin API key (`ADMIN_API_KEY` in `.env`)
- JWT auth planned for production Admin UI (ADR — future scope)
- All admin actions logged to audit trail
- Rate limiting: admin endpoints exempt from consumer rate limits

---

## Related

- `docs/13-Premortem.md`: G01-B — Config UI design prescribed here
- `docs/06-HLD.md`: Section 2.6 — Configuration Management
- `docs/decisions/ADR-001-tech-stack.md`: React 18 + MUI selection
