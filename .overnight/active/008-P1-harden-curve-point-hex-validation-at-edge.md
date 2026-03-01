---
id: 8
title: "Harden curve point / hex validation in Zod schemas to return 400 not 500"
priority: P1
severity: medium
status: completed
source: gap_analyzer
file: src/utils/schemas.ts
line: 1
created: "2026-02-28T00:00:00Z"
execution_hint: parallel
context_group: infrastructure
group_reason: "Independent from other tasks — only touches src/utils/schemas.ts. Can run in parallel."
---

# Harden curve point / hex validation in Zod schemas to return 400 not 500

**Priority:** P1 (medium — invalid inputs cause 500 instead of 400)
**Source:** gap_analyzer
**Location:** src/utils/schemas.ts, src/core/crypto/bdhke.ts

## Problem

Route-level Zod schemas only check that `B_` (blinded message) and `C` (proof) fields are non-empty strings — no hex format validation, no curve-point validity check. When a wallet sends an invalid hex string or a point not on the secp256k1 curve, the error propagates through `fromHex()` / `assertValidity()` in the crypto layer and bubbles up as an uncaught exception, causing Fastify to return a generic 500 error.

Per the Cashu spec (NUT-00), invalid points should return a 400 `Bad Request` with a meaningful error message, not a 500.

Current schema (too permissive):
```typescript
// src/utils/schemas.ts — only checks non-empty
const blindedMessageSchema = z.object({
  amount: z.number().int().positive(),
  B_: z.string().min(1),  // ← no hex validation
  id: z.string(),
});
```

## How to Fix

**Step 1 — Add a reusable hex33 point validator to src/utils/schemas.ts:**
```typescript
// Validates a compressed secp256k1 point: 02/03 prefix + 32 bytes = 66 hex chars
const hexPoint = z.string()
  .regex(/^(02|03)[0-9a-fA-F]{64}$/, 'Must be a compressed secp256k1 point (66 hex chars, 02/03 prefix)');

// Uncompressed points (04 prefix + 64 bytes = 130 chars) are not used in Cashu
```

**Step 2 — Apply the validator to B_ and C fields in all relevant schemas:**
```typescript
const blindedMessageSchema = z.object({
  amount: z.number().int().positive(),
  B_: hexPoint,   // ← validated
  id: z.string().min(1),
});

const proofSchema = z.object({
  amount: z.number().int().positive(),
  id: z.string().min(1),
  secret: z.string().min(1),
  C: hexPoint,    // ← validated
});
```

**Step 3 — Verify affected schemas:**
Identify all schemas in `src/utils/schemas.ts` that contain `B_` or `C` fields (swap, mint, melt, checkstate routes) and apply the `hexPoint` validator.

**Step 4 — Verify error surfacing:**
Zod parse errors in route handlers should already return 400 via the existing `catch (err)` blocks. If not, confirm Fastify's `schemaErrorFormatter` or the route error handler properly surfaces Zod errors as 400.

## Acceptance Criteria

- [ ] `hexPoint` (or equivalent) Zod refinement added to `src/utils/schemas.ts`
- [ ] All `B_` and `C` fields in request schemas use `hexPoint` validator
- [ ] Sending a non-hex string for `B_` or `C` returns HTTP 400 with descriptive error
- [ ] Sending a valid hex but non-curve-point returns HTTP 400 (regex catches wrong-length/prefix)
- [ ] Existing valid requests still work (no regressions)
- [ ] `npm run typecheck` passes
- [ ] `npm test` passes

## Notes

_Generated from gap_analyzer (P1, effort=low). Prevents crypto errors from leaking as 500s. The regex approach catches malformed inputs; deeper curve-point validation can be added as a Zod `.refine()` if needed._
