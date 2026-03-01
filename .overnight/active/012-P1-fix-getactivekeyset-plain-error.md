---
id: 12
title: "Fix getActiveKeyset() throws plain Error — use typed CashuError subclass"
priority: P1
severity: high
status: completed
source: code_quality_audit
file: src/services/mint-service.ts
line: 573
created: "2026-02-28T06:00:00Z"
execution_hint: sequential
context_group: mint_service_errors
group_reason: "Same file as task 013 (mint-service.ts). Both fix error handling in MintService."
---

# Fix getActiveKeyset() throws plain Error — use typed CashuError subclass

**Priority:** P1 (high — causes unstructured 500 responses in production)
**Source:** code_quality_audit
**Location:** src/services/mint-service.ts:571–577

## Problem

`getActiveKeyset()` throws a plain `Error` instead of a typed `CashuError` subclass. All other error paths in `MintService` use typed `CashuError` subclasses. Route handlers catch `instanceof CashuError` and return structured 400 responses — a plain `Error` escapes this handler and becomes an **unstructured 500 response** to the client.

**Code with issue:**
```typescript
// mint-service.ts:571–577
private getActiveKeyset(): KeysetState {
    const ks = this.keysets.get(this.activeKeysetId);
    if (!ks) {
        throw new Error('No active keyset — call init() first');  // ← plain Error
    }
    return ks;
}
```

**Contrast with adjacent method:**
```typescript
// mint-service.ts:579–584 — correct pattern
private getKeysetForProof(keysetId: string): KeysetState {
    const ks = this.keysets.get(keysetId);
    if (!ks) {
        throw new KeysetNotFoundError(`Keyset ${keysetId} not found`);  // ← typed
    }
    return ks;
}
```

This inconsistency means that if the mint ever starts in an uninitialized state (e.g., `init()` not called before requests arrive during startup), all endpoints calling `getActiveKeyset()` will return unstructured 500 errors instead of a diagnostic 400 with an error code.

## How to Fix

Replace the plain `Error` throw with `KeysetNotFoundError` (already defined in `src/core/errors.ts`) since the semantics are the same — the active keyset is not found in the in-memory map:

```typescript
private getActiveKeyset(): KeysetState {
    const ks = this.keysets.get(this.activeKeysetId);
    if (!ks) {
        throw new KeysetNotFoundError('No active keyset — call init() first');
    }
    return ks;
}
```

Alternatively, create a `MintNotInitializedError` extending `CashuError` if a more specific error code is warranted. Check `src/core/errors.ts` for existing error codes and conventions before adding a new subclass.

## Acceptance Criteria

- [ ] `getActiveKeyset()` no longer throws a plain `Error`
- [ ] Uses `KeysetNotFoundError` or a new typed `CashuError` subclass
- [ ] Route-level error handlers will now produce a structured 400 response (not a 500) if active keyset is missing
- [ ] `npm run typecheck` passes
- [ ] `npm test` passes

## Notes

_Generated from code_quality_audit (HIGH severity — inconsistent error handling causes unstructured 500s)._
