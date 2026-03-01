---
id: 1
title: "Bootstrap project with Python/FastAPI tech stack"
priority: P0
severity: critical
status: completed
source: conductor_synthesis
file: ""
line: 0
created: "2026-02-28T00:00:00"
execution_hint: sequential
context_group: infrastructure
group_reason: "Must complete first — everything else depends on project scaffold"
---

# Bootstrap project with Python/FastAPI tech stack

**Priority:** P0 (critical)
**Source:** conductor_synthesis
**Location:** project root

## Problem

The cashu-mint project is a completely empty directory with zero source code, zero configuration files, and zero documentation. Before any protocol features can be implemented, the project must be bootstrapped with:
- A chosen programming language and web framework
- Package management and dependency files
- Basic project structure (source dirs, tests dir, config)
- A runnable (even empty) HTTP server
- Development tooling (linting, formatting, type checking)

Without this foundation, no other work can begin. The project has 0% implementation coverage across all 24 required features.

## How to Fix

Bootstrap a Python + FastAPI project (recommended: matches Nutshell reference implementation, well-understood in the Cashu community):

1. Create `pyproject.toml` or `requirements.txt` with dependencies:
   - `fastapi` (web framework)
   - `uvicorn` (ASGI server)
   - `sqlalchemy` + `alembic` (ORM + migrations)
   - `pydantic` (data validation)
   - `cryptography` or `coincurve` (secp256k1 operations)
   - `pytest` + `httpx` (testing)

2. Create project structure:
   ```
   cashu_mint/
     __init__.py
     main.py          # FastAPI app entry point
     config.py        # Configuration
     db/              # Database models + migrations
     crypto/          # BDHKE cryptographic engine
     lightning/       # Lightning backend abstraction
     nuts/            # NUT implementations (one module per NUT)
     models/          # Pydantic request/response models
   tests/
     unit/
     integration/
   ```

3. Create `main.py` with a minimal FastAPI app that starts successfully

4. Add `.gitignore`, `README.md` stub, `Dockerfile` stub

5. Verify: `uvicorn cashu_mint.main:app --reload` starts without errors

Reference: https://github.com/cashubtc/nutshell (Python reference implementation)

## Acceptance Criteria

- [ ] `pyproject.toml` or `requirements.txt` exists with all required dependencies
- [ ] Project directory structure is created
- [ ] `uvicorn cashu_mint.main:app` starts successfully (returns 404 on unknown routes, 200 on health check)
- [ ] `pytest` runs without errors (even with 0 tests)
- [ ] `.gitignore` covers Python artifacts, venv, secrets
- [ ] No hardcoded secrets in any committed file

## Notes

_Generated from conductor synthesis — greenfield bootstrap is prerequisite for all other tasks._
