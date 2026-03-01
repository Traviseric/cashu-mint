---
id: 14
title: "Remove dead getProofStates() export from repository.ts"
priority: P2
severity: medium
status: completed
source: code_quality_audit
file: src/db/repository.ts
line: 356
created: "2026-02-28T06:00:00Z"
execution_hint: parallel
context_group: independent
group_reason: "Standalone dead code removal in repository.ts. No file overlap with tasks 011-013."
---

# Remove dead getProofStates() export from repository.ts

**Priority:** P2 (medium — dead export creates confusion about which function to use)
**Source:** code_quality_audit
**Location:** src/db/repository.ts:356

## Problem

`getProofStates(secrets: string[])` is exported from `repository.ts` but is **never called anywhere** in the codebase. It was superseded by `getProofStatesByY()` which queries by Y-point (hash_to_curve of secret) as required by NUT-07. Having both functions exported creates ambiguity about which one to use — future contributors might reach for the wrong one.

**Dead code:**
```typescript
// repository.ts:356 — never called
export async function getProofStates(secrets: string[]): Promise<Map<string, 'SPENT' | 'PENDING'>> {
    // queries by raw secret string — superseded by getProofStatesByY()
    ...
}
```

**Active replacement (used in mint-service.ts:518):**
```typescript
export async function getProofStatesByY(Ys: string[]): Promise<Map<string, ProofState>>
```

## How to Fix

Delete the `getProofStates()` function from `repository.ts`. Verify no imports of it exist anywhere first:

```bash
grep -rn "getProofStates[^B]" src/
```

If no callers exist (confirmed by grep), remove the function body and its export.

## Acceptance Criteria

- [ ] `getProofStates()` function removed from `src/db/repository.ts`
- [ ] No callers of `getProofStates()` exist anywhere in `src/`
- [ ] `getProofStatesByY()` remains untouched
- [ ] `npm run typecheck` passes
- [ ] `npm test` passes

## Notes

_Generated from code_quality_audit (MEDIUM severity — dead export causes confusion, superseded by getProofStatesByY())._
