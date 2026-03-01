---
id: 15
title: "Fix redundant witness patterns — remove no-op ?? undefined and ternary"
priority: P3
severity: low
status: completed
source: code_quality_audit
file: src/db/repository.ts
line: 103
created: "2026-02-28T06:00:00Z"
execution_hint: parallel
context_group: independent
group_reason: "Quick cleanup across repository.ts and mint-service.ts. No dependency on other tasks."
---

# Fix redundant witness patterns — remove no-op ?? undefined and ternary

**Priority:** P3 (low — no-op patterns add noise to the codebase)
**Source:** code_quality_audit
**Location:** src/db/repository.ts:103,291,326 and src/services/mint-service.ts:208,463

## Problem

Two redundant patterns appear multiple times across the codebase:

**Pattern 1 — `witness ?? undefined` is a no-op (repository.ts:103,291,326):**
```typescript
witness: p.witness ?? undefined,
```
`null ?? undefined` evaluates to `undefined`. `undefined ?? undefined` also evaluates to `undefined`. This is equivalent to just `witness: p.witness` and adds no value.

**Pattern 2 — Redundant ternary (mint-service.ts:208,463):**
```typescript
witness: p.witness ? p.witness : undefined,
```
`p.witness` is already either a string or `undefined`/`null`. The ternary adds no transformation — it's equivalent to `witness: p.witness ?? undefined` (same no-op) or just `witness: p.witness`.

## How to Fix

Replace all occurrences with `witness: p.witness`:

**repository.ts (lines 103, 291, 326):**
```typescript
// Before:
witness: p.witness ?? undefined,

// After:
witness: p.witness,
```

**mint-service.ts (lines 208, 463):**
```typescript
// Before:
witness: p.witness ? p.witness : undefined,

// After:
witness: p.witness,
```

Run a search to catch all occurrences:
```bash
grep -n "witness.*??" src/db/repository.ts
grep -n "witness.*?" src/services/mint-service.ts
```

## Acceptance Criteria

- [ ] All `witness: p.witness ?? undefined` replaced with `witness: p.witness` in repository.ts (3 locations)
- [ ] All `witness: p.witness ? p.witness : undefined` replaced with `witness: p.witness` in mint-service.ts (2 locations)
- [ ] `npm run typecheck` passes
- [ ] `npm test` passes

## Notes

_Generated from code_quality_audit (LOW severity — two findings merged: no-op ?? undefined pattern MEDIUM + redundant ternary LOW, both about witness field)._
