# LLM Gateway — AI Development Agents

## Purpose

This directory contains **development-time AI agents and skills** for the LLM Gateway Technothon project.
These are tools to improve architecture quality, implementation velocity, testing quality, and documentation quality.

> **Critical Boundary**: These agents are development tools only.
> They must never replace, simulate, or interfere with runtime services.

---

## Runtime vs. Development Separation

| Layer | Components | Owned By |
|-------|-----------|----------|
| **Runtime** | Model Router, Failover Service, Semantic Cache, Queue Manager, Rate Limiter, Analytics Service | `src/` |
| **Development AI** | Architecture Agent, Implementation Agent, Testing Agent, Documentation Agent | `.agents/` |

Agents operate **exclusively** on source code, documentation, and test artefacts.
They do **not** call runtime APIs, manage provider connections, or mutate `data/analytics.json` in production.

---

## Directory Structure

```
.agents/
├── README.md                          ← this file
├── skills/
│   ├── architecture-skill.md          ← system design & ADR guidance
│   ├── backend-gateway-skill.md       ← gateway, routing, cache, queue
│   ├── frontend-dashboard-skill.md    ← React config UI & analytics dashboard
│   ├── testing-skill.md               ← unit, integration, load testing
│   └── devops-skill.md                ← CI/CD, Docker, Kubernetes, monitoring
├── architecture-review-agent.md       ← reviews architecture against rubrics
├── implementation-agent.md            ← generates & reviews implementation code
├── testing-agent.md                   ← generates & runs test suites
└── documentation-agent.md             ← generates docs, diagrams, ADRs
```

---

## Skills (`.agents/skills/`)

Skills are **reusable knowledge profiles** that agents load when working on a specific domain.

| Skill | Domain | Key Knowledge Areas |
|-------|--------|---------------------|
| `architecture-skill` | System Design | NFR mapping, failover chains, scoring algorithm, tech selection |
| `backend-gateway-skill` | Python / FastAPI | NFR parser, model selector, semantic cache, provider abstraction |
| `frontend-dashboard-skill` | React / TypeScript | Config UI, analytics dashboard, chart integration |
| `testing-skill` | pytest / Locust | Unit, integration, load tests; coverage targets |
| `devops-skill` | Docker / K8s / GitHub Actions | CI pipeline, container builds, monitoring, secrets |

---

## Agents (`.agents/`)

Agents are **role-defined assistants** that use one or more skills to perform a bounded task.

| Agent | Permitted Actions | Forbidden Actions |
|-------|-------------------|-------------------|
| `architecture-review-agent` | Analyse design, validate against rubrics, suggest improvements | Modify runtime config, add unneeded services |
| `implementation-agent` | Generate / review code in `src/` | Replace runtime services, add new microservices without justification |
| `testing-agent` | Write tests, measure coverage, run test suites | Mutate production data, call live LLM provider APIs |
| `documentation-agent` | Write docs, generate diagrams, update README | Change source code, modify CI pipelines |

---

## Permitted vs. Forbidden Actions (All Agents)

### Permitted
- Analyse code in `src/`, `tests/`, `docs/`, `demo/`
- Suggest changes and improvements
- Generate new code, tests, and documentation
- Review implementation against project rubrics
- Create Architecture Decision Records (ADRs)

### Forbidden
- Replace backend runtime services with AI agent logic
- Create unnecessary abstractions or wrapper classes
- Introduce new microservices without explicit justification mapped to a project requirement
- Hard-code API keys or secrets in any generated artefact
- Modify files under `data/` in a production context

---

## Project Targets (Reference)

Agents must generate artefacts that help achieve or maintain:

| Metric | Target |
|--------|--------|
| P95 latency (cached) | < 500 ms |
| P95 latency (uncached) | < 2 s |
| Cache hit rate | > 40 % |
| Cost reduction | > 45 % |
| Test coverage | > 80 % |
| Critical security vulnerabilities | 0 |
| Failover time | < 500 ms |
| Availability | > 99.95 % |

---

*All agents and skills are scoped to the Propeller Technothon — Problem Statement 4: LLM Gateway Platform.*
