# ADR-006: Use `py` Launcher Instead of `python` on Windows

> Status: Accepted | Date: POC Phase | Deciders: Architecture Team

---

## Context

On Windows 11, the `python` command is not always mapped to the installed Python interpreter. Windows may resolve `python` to the Microsoft Store stub, which opens the Store instead of running Python. The Python Launcher (`py`) is the correct Windows-native entry point.

## Problem

```powershell
# Fails on Windows (resolves to Store stub or "not found"):
python -m uvicorn src.api.main:app --reload

# Also fails:
python -m pytest tests/
```

## Decision

Use the **`py` launcher** for all Python invocations on Windows. All Windows-specific instructions in documentation reference `py` instead of `python`.

## Correct Windows Commands

```powershell
# Install dependencies
py -m pip install --prefer-binary -r requirements.txt

# Set PYTHONPATH
$env:PYTHONPATH = "."

# Start gateway
py -m uvicorn src.api.main:app --reload --port 8000

# Run tests
py -m pytest --cov=src tests/

# Run demo
py demo/run_demo_v2.py

# Seed demo data
py demo/seed_demo_data.py
```

## Why `--prefer-binary`

Some packages (e.g. `httptools`, `uvloop`) require C compilation on install. `--prefer-binary` instructs pip to use pre-compiled wheels where available, avoiding build failures on Windows where MSVC may not be configured.

## Consequences

- **Positive:** Gateway starts successfully on Windows 11 with no PATH configuration required
- **Positive:** All tests pass on Windows using `py -m pytest`
- **Positive:** No system PATH changes needed
- **Negative:** Documentation must maintain two sets of commands (Linux/macOS vs. Windows)
- **Mitigation:** `docs/guides/setup_guide.md` Windows section documents all commands explicitly

## Related

- ADR-005: Remove emojis from source files (Windows encoding)
- `docs/guides/setup_guide.md`: Windows Setup section
