# Monitoring Guide — LLM Gateway Platform

> Status: Documented | Implementation: Full Stack (Path B only)
> POC: Metrics available via GET /v1/analytics/summary
> Production: Grafana + Prometheus (docker-compose up)

---

## Overview

The monitoring stack provides real-time observability across all gateway dimensions:
- Request throughput and latency (P50, P95, P99)
- Cache hit rate and cost savings
- Provider health and circuit breaker states
- Tier quota utilisation
- Error rates and failover events

---

## Stack Components

| Component | Technology | Port | Purpose |
|-----------|-----------|------|---------|
| Metrics scraper | Prometheus 2.45 | 9090 | Pull metrics from gateway `/metrics` endpoint |
| Dashboard | Grafana 10 | 3001 | Visualise all metrics |
| Dashboard definition | `monitoring/grafana/dashboards/llm-gateway.json` | — | Pre-built dashboard JSON |
| Gateway metrics | FastAPI `/metrics` (Prometheus format) | 8000 | Exposes all counters and histograms |

---

## Grafana Dashboard Panels (6 Panels)

### Panel 1 — Request Throughput (RPS)
```promql
rate(gateway_requests_total[1m])
```
- Type: Time-series line chart
- Breakdown: by tier, by provider

### Panel 2 — Latency Percentiles
```promql
histogram_quantile(0.95, rate(gateway_latency_ms_bucket[5m]))
histogram_quantile(0.50, rate(gateway_latency_ms_bucket[5m]))
```
- Type: Time-series line chart
- Targets: P50 < 720ms, P95 < 1840ms

### Panel 3 — Cache Hit Rate
```promql
rate(gateway_cache_hits_total[5m]) /
rate(gateway_requests_total[5m])
```
- Type: Stat panel + time-series
- Target: > 40% (NFR-04)

### Panel 4 — Cost Tracking
```promql
increase(gateway_cost_usd_total[1h])
increase(gateway_cost_saved_usd_total[1h])
```
- Type: Stat panel (current hour cost + savings)
- Target: Savings > 45% of gross cost (NFR-05)

### Panel 5 — Provider Health & Circuit Breakers
```promql
gateway_circuit_breaker_state{provider="openai"}
gateway_circuit_breaker_state{provider="anthropic"}
gateway_circuit_breaker_state{provider="google"}
```
- Type: State timeline (0=CLOSED, 1=HALF-OPEN, 2=OPEN)
- Alerts: OPEN state > 30s triggers notification

### Panel 6 — Error Rate
```promql
rate(gateway_errors_total[5m]) /
rate(gateway_requests_total[5m])
```
- Type: Stat panel with threshold colouring
- Target: < 0.1% (NFR-06)

---

## Setup (Full Stack — Path B)

### Step 1: Start Monitoring Stack

```bash
docker-compose up -d prometheus grafana
```

### Step 2: Verify Prometheus is Scraping

```bash
curl http://localhost:9090/api/v1/targets
# Confirm gateway target is UP
```

### Step 3: Import Grafana Dashboard

1. Open Grafana at http://localhost:3001
2. Login: `admin` / `admin` (change on first login)
3. Navigate to **Dashboards → Import**
4. Click **Upload JSON file**
5. Select `monitoring/grafana/dashboards/llm-gateway.json`
6. Click **Import**

### Step 4: Verify Dashboard

The LLM Gateway dashboard should display all 6 panels populated with live data within 15 seconds of the first request.

---

## Prometheus Metrics Exposed by Gateway

| Metric | Type | Labels | Description |
|--------|------|--------|-------------|
| `gateway_requests_total` | Counter | tier, provider, model, cache_hit | Total requests processed |
| `gateway_latency_ms` | Histogram | model, provider, cache_hit | Request latency in ms |
| `gateway_cache_hits_total` | Counter | — | Total cache hits |
| `gateway_cost_usd_total` | Counter | provider, model | Cumulative cost in USD |
| `gateway_cost_saved_usd_total` | Counter | — | Cost saved via cache |
| `gateway_errors_total` | Counter | error_type, provider | Total errors |
| `gateway_failover_total` | Counter | from_provider, to_provider, level | Failover events |
| `gateway_circuit_breaker_state` | Gauge | provider | 0=CLOSED, 1=HALF-OPEN, 2=OPEN |
| `gateway_queue_depth` | Gauge | tier | Current queue depth per tier |

---

## Alerting Rules (Production)

```yaml
# monitoring/prometheus/alerts.yml
groups:
  - name: llm-gateway
    rules:
      - alert: HighErrorRate
        expr: rate(gateway_errors_total[5m]) / rate(gateway_requests_total[5m]) > 0.001
        for: 2m
        labels:
          severity: critical
        annotations:
          summary: "Error rate > 0.1% for 2 minutes"

      - alert: CircuitBreakerOpen
        expr: gateway_circuit_breaker_state > 0
        for: 30s
        labels:
          severity: warning
        annotations:
          summary: "Circuit breaker {{ $labels.provider }} is OPEN"

      - alert: CacheHitRateLow
        expr: rate(gateway_cache_hits_total[10m]) / rate(gateway_requests_total[10m]) < 0.30
        for: 10m
        labels:
          severity: warning
        annotations:
          summary: "Cache hit rate below 30% for 10 minutes"
```

---

## POC Alternative (Path A — No Docker)

In the POC setup, monitoring is available via the analytics REST API:

```bash
curl http://localhost:8000/v1/analytics/summary \
  -H "Authorization: Bearer demo-key"
```

This returns all key metrics in JSON format. See `docs/evidence/analytics-summary-output.md` for a verified sample response.

---

## Related

- `monitoring/grafana/dashboards/llm-gateway.json` — Dashboard definition
- `docs/guides/setup_guide.md` — Path B setup (docker-compose)
- `docs/evidence/analytics-summary-output.md` — POC analytics evidence
- ADR-010: JSON analytics store (POC); TimescaleDB (production)
