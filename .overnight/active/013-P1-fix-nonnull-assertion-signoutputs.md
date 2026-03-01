---
id: 13
title: "Fix non-null assertion in signOutputs() — add explicit null check with typed error"
priority: P1
severity: high
status: completed
source: code_quality_audit
file: src/services/mint-service.ts
line: 634
created: "2026-02-28T06:00:00Z"
execution_hint: sequential
context_group: mint_service_errors
group_reason: "Same file as task 012 (mint-service.ts). Both fix error handling in MintService."
---

# Fix non-null assertion in signOutputs() — add explicit null check with typed error

**Priority:** P1 (high — implicit call-order coupling, unhandled TypeError at runtime)
**Source:** code_quality_audit
**Location:** src/services/mint-service.ts:634

## Problem

`signOutputs()` uses a non-null assertion operator (`!`) on `this.keysets.get(output.id)!`. This method implicitly assumes `validateOutput()` was always called first to verify the keyset exists. That relationship is not enforced by the type system — it's a convention.

If `signOutputs()` is ever called without a prior `validateOutput()` call (e.g., during future refactoring, code reuse, or test scenarios), this throws an **unhandled `TypeError`** at runtime: `Cannot read properties of undefined (reading 'privateKeys')`.

**Code with issue:**
```typescript
// mint-service.ts:631–643
private signOutputs(outputs: BlindedMessage[]): BlindSignature[] {
    return outputs.map((output) => {
        const keyset = this.keysets.get(output.id)!;  // ← non-null assertion
        const privKey = keyset.privateKeys[String(output.amount)];
        const C_ = signBlindedMessage(output.B_, privKey);
        return {
            amount: output.amount,
            id: output.id,
            C_,
        };
    });
}
```

## How to Fix

Remove the `!` assertion and add an explicit null check that throws a typed `KeysetNotFoundError`:

```typescript
private signOutputs(outputs: BlindedMessage[]): BlindSignature[] {
    return outputs.map((output) => {
        const keyset = this.keysets.get(output.id);
        if (!keyset) {
            throw new KeysetNotFoundError(`Keyset ${output.id} not found`);
        }
        const privKey = keyset.privateKeys[String(output.amount)];
        const C_ = signBlindedMessage(output.B_, privKey);
        return {
            amount: output.amount,
            id: output.id,
            C_,
        };
    });
}
```

`KeysetNotFoundError` is already imported/defined in `src/core/errors.ts`. This makes the failure mode explicit and typed — callers get a structured CashuError response instead of an unhandled TypeError.

## Acceptance Criteria

- [ ] Non-null assertion `!` removed from `signOutputs()`
- [ ] Explicit null check added with `KeysetNotFoundError` (or equivalent typed error)
- [ ] No unhandled TypeError if keyset is missing from the in-memory map
- [ ] `npm run typecheck` passes
- [ ] `npm test` passes

## Notes

_Generated from code_quality_audit (HIGH severity — non-null assertion relies on implicit call-order coupling, risks unhandled TypeError)._
