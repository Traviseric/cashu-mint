---
id: 10
title: "Implement keyset rotation — load historical keysets on startup, add rotation trigger"
priority: P1
severity: medium
status: completed
source: gap_analyzer + feature_audit
file: src/services/mint-service.ts
line: 1
created: "2026-02-28T00:00:00Z"
execution_hint: sequential
context_group: keyset_management
group_reason: "Standalone feature touching mint-service.ts and repository.ts. Independent from melt_flow group."
---

# Implement keyset rotation — load historical keysets on startup, add rotation trigger

**Priority:** P1 (medium — keyset rotation claimed but unimplemented)
**Source:** gap_analyzer + feature_audit
**Location:** src/services/mint-service.ts, src/db/repository.ts

## Problem

NUT-02 keyset rotation is claimed in CLAUDE.md ("old keysets stay spendable (redeem) but not issuable (new mints)") and the `deactivateKeyset()` method exists in `repository.ts`. However:

1. `MintService.init()` always creates a **single keyset from index 0** — it never loads existing keysets from the DB on startup.
2. There is no API endpoint or mechanism to trigger keyset rotation.
3. There is no support for loading multiple historical keysets from DB into the in-memory map.
4. The `validateOutput` function correctly rejects inactive keyset IDs, but since only one keyset ever exists in memory, a restarted server with a rotated keyset would be unable to verify old proofs.

If a keyset were rotated (manually via DB or future admin API), a server restart would lose access to the old keyset and reject valid spends of old tokens.

## How to Fix

**Step 1 — Load ALL active and historical keysets from DB on init:**

Update `MintService.init()`:
```typescript
async init(): Promise<void> {
  // Load ALL existing keysets from DB into memory (active + inactive)
  const allKeysets = await this.repo.getAllKeysets();

  for (const keyset of allKeysets) {
    const keys = regenerateKeysFromKeyset(keyset); // derive keys from stored id/unit/index
    this.keysets.set(keyset.id, { keyset, keys });
  }

  // Determine current active keyset (highest index for default unit)
  const activeKeyset = allKeysets
    .filter(k => k.active && k.unit === 'sat')
    .sort((a, b) => b.derivationIndex - a.derivationIndex)[0];

  if (!activeKeyset) {
    // No keyset exists — derive and create the first one
    await this._createNewKeyset(0);
  } else {
    this.activeKeysetId = activeKeyset.id;
  }
}
```

**Step 2 — Add `getAllKeysets()` to repository.ts:**
```typescript
async getAllKeysets(): Promise<Keyset[]> {
  return this.prisma.keyset.findMany({ orderBy: { derivationIndex: 'asc' } });
}
```

Also add `derivationIndex` field to the `Keyset` model in `prisma/schema.prisma` if not present:
```prisma
model Keyset {
  id              String  @id
  unit            String  @default("sat")
  active          Boolean @default(true)
  derivationIndex Int     @default(0)
  // ... existing fields
}
```

**Step 3 — Add a rotation method to MintService:**
```typescript
async rotateKeyset(): Promise<{ newKeysetId: string }> {
  // Deactivate current active keyset
  await this.repo.deactivateKeyset(this.activeKeysetId);

  // Derive next keyset (index + 1)
  const nextIndex = this.currentKeysetIndex + 1;
  const newKeyset = await this._createNewKeyset(nextIndex);

  this.activeKeysetId = newKeyset.id;
  return { newKeysetId: newKeyset.id };
}
```

**Step 4 — (Optional) Add admin rotation endpoint:**
```typescript
// src/routes/v1/admin.ts (or inside keys.ts)
server.post('/v1/admin/rotate-keyset', async (req, reply) => {
  // Could be protected by an admin token in config
  const result = await mintService.rotateKeyset();
  return result;
});
```

**Step 5 — Ensure `validateOutput` and `validateProof` use the full in-memory keyset map:**
Verify that proof verification looks up keysets by ID from `this.keysets` map (not just the active keyset), so old proofs remain spendable after rotation.

## Acceptance Criteria

- [ ] `getAllKeysets()` added to repository.ts
- [ ] `MintService.init()` loads all historical keysets from DB into memory on startup
- [ ] `MintService.rotateKeyset()` method added (deactivates old, derives new)
- [ ] After rotation + server restart, old proofs are still spendable (old keyset loaded from DB)
- [ ] After rotation, new mints use the new keyset ID
- [ ] `derivationIndex` field added to Keyset schema if missing
- [ ] `npm run typecheck` passes
- [ ] `npm test` passes

## Notes

_Generated from gap_analyzer (P1) + feature_audit (medium severity). CLAUDE.md claims this behavior already works — this task makes the claim true._
