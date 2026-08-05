# AI Agent Development Context

## Purpose

This document defines how AI coding assistants and development agents should support the LLM Gateway project.

## Project Reference

Primary technical source:
- PROJECT_CONTEXT.md

## Objective

Use AI assistants to improve:
- architecture quality
- implementation velocity
- testing quality
- documentation quality

Do not change the runtime architecture.

## AI Skills Required

1. Architecture Skill
2. Backend Gateway Skill
3. Frontend Dashboard Skill
4. Testing Skill
5. DevOps Skill

## Development Agents Required

1. Architecture Review Agent
2. Implementation Agent
3. Testing Agent
4. Documentation Agent

## Agent Boundaries

AI development agents may:
- analyze code
- suggest changes
- generate code
- generate tests
- review implementation

AI development agents must not:
- replace backend services with AI agents
- create unnecessary abstractions
- introduce new microservices without justification

## Runtime vs Development Separation

Runtime components:
- Model Router
- Failover Service
- Semantic Cache
- Queue Manager
- Rate Limiter
- Analytics Service

Development AI components:
- Architecture Agent
- Implementation Agent
- Testing Agent
- Documentation Agent

Keep these separate.

---

# Agent Workflow

For every development task, follow this order:

1. Architecture Review Agent
   - Review requirements
   - Check architecture impact
   - Approve approach

2. Implementation Agent
   - Make approved changes
   - Follow project boundaries

3. Testing Agent
   - Validate changes
   - Add or update tests

4. Documentation Agent
   - Update documentation if needed


# Remediation Priority

Fix issues in this order:

1. Critical
2. High
3. Medium
4. Low


# Completion Rules

A task is complete only when:

- Architecture is approved
- Implementation is completed
- Tests pass
- Documentation is updated when required
