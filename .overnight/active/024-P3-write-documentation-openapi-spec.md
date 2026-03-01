---
id: 24
title: "Write documentation, README, and OpenAPI spec"
priority: P3
severity: low
status: pending
source: feature_audit
file: "README.md"
line: 0
created: "2026-02-28T00:00:00"
execution_hint: parallel
context_group: quality
group_reason: "Documentation is independent and can be written in parallel with any other task"
---

# Write documentation, README, and OpenAPI spec

**Priority:** P3 (low)
**Source:** feature_audit / gap_analyzer
**Location:** README.md

## Problem

No documentation or OpenAPI spec. The mint API should have a machine-readable spec and operator setup guide.

Without documentation:
- New operators cannot set up the mint
- Wallet developers cannot understand the API
- The project is not presentable to the Cashu community

## How to Fix

1. **README.md** covering:
   - Project description and Cashu protocol overview
   - Prerequisites (Python 3.11+, Lightning node)
   - Installation: `pip install -e .` or `pip install -r requirements.txt`
   - Configuration: copy `.env.example` to `.env`, fill in values
   - Running: `uvicorn cashu_mint.main:app --reload`
   - Lightning backends supported (LNbits, LND, CLN, Fake for testing)
   - NUT support matrix (which NUTs are implemented)
   - Contributing guide

2. **OpenAPI spec** — FastAPI auto-generates this at `/docs` and `/redoc`. Ensure:
   - All endpoint models have Pydantic field descriptions
   - Request/response examples included in model schemas
   - Error responses documented with example bodies
   - Tags used to group endpoints by NUT number

3. **CLAUDE.md** — context for AI-assisted development:
   - Tech stack and key decisions
   - Testing instructions
   - Where to find NUT specs
   - Coding conventions

Steps:
1. Write comprehensive README.md
2. Add `description` fields to all Pydantic models for OpenAPI docs
3. Add request/response examples to key endpoints
4. Verify FastAPI docs UI at /docs shows all endpoints correctly
5. Create CLAUDE.md with project context for future development sessions

## Acceptance Criteria

- [ ] README.md explains setup from zero to running mint
- [ ] GET /docs shows all endpoints with request/response schemas
- [ ] NUT support matrix table in README is accurate
- [ ] `.env.example` referenced and documented in README
- [ ] CLAUDE.md created with tech stack context

## Notes

_Generated from feature_audit finding: Documentation & API Spec (low, effort: low)._
