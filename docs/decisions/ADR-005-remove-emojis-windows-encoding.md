# ADR-005: Remove Emoji Characters from Source Files (Windows cp1252 Encoding)

> Status: Accepted | Date: POC Phase | Deciders: Architecture Team

---

## Context

During local development and CI execution on Windows, Python raised `UnicodeEncodeError: 'charmap' codec can't encode character` errors when source files contained emoji characters (e.g. ✅, ⚠️, 🔴). Windows uses the cp1252 codec by default for console output, which cannot encode Unicode emoji outside its range.

## Problem

```
UnicodeEncodeError: 'charmap' codec can't encode character '\u2705'
in position 12: character maps to <undefined>
```

This caused the gateway to crash on startup and all tests to fail on Windows environments.

## Decision

**Remove all emoji characters from all Python source files.** Documentation files (`.md`) may retain emojis as they are rendered by Markdown viewers, not executed by Python.

## Scope

| File Type | Action |
|-----------|--------|
| `*.py` source files | All emojis removed — replaced with text equivalents |
| `*.md` documentation | Emojis retained (rendered by viewer, not Python) |
| `.env` / config files | No emojis used |
| Log strings | Text-only status indicators used |

## Resolution Applied

```python
# Before (caused crash on Windows):
logger.info("✅ Cache hit for prompt")
logger.info("⚠️ Provider failure — triggering failover")

# After (Windows-safe):
logger.info("[CACHE HIT] Cache hit for prompt")
logger.info("[FAILOVER] Provider failure - triggering failover")
```

## Consequences

- **Positive:** Gateway runs without errors on Windows 11 with default cp1252 encoding
- **Positive:** All 8 demo scenarios verified PASS on Windows after fix
- **Positive:** CI pipeline passes on all platforms
- **Negative:** Slightly less visually expressive log output
- **Mitigation:** Log prefixes (`[CACHE HIT]`, `[FAILOVER]`) are equally scannable

## Related

- ADR-006: Use `py` launcher on Windows
- `docs/guides/setup_guide.md`: Windows Setup section
