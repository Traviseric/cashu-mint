---
id: 7
title: "Add CORS support so browser-based Cashu wallets can connect"
priority: P1
severity: high
status: completed
source: gap_analyzer
file: src/server.ts
line: 1
created: "2026-02-28T00:00:00Z"
execution_hint: parallel
context_group: infrastructure
group_reason: "Independent infrastructure fix — touches only server.ts and package.json. No overlap with other tasks."
---

# Add CORS support so browser-based Cashu wallets can connect

**Priority:** P1 (high — browser wallets blocked without CORS)
**Source:** gap_analyzer
**Location:** src/server.ts, package.json

## Problem

No CORS configuration exists. `@fastify/cors` is not installed. Browser-based Cashu wallets (e.g., Nutstash, cashu.me) make cross-origin requests to mints. Without CORS headers, all these requests are blocked by browser security policy with a CORS error, making the mint unusable from any web wallet.

Current state: No `Access-Control-Allow-Origin` headers are set on any response.

## How to Fix

**Step 1 — Install @fastify/cors:**
```bash
npm install @fastify/cors
```

**Step 2 — Register CORS plugin in src/server.ts:**
```typescript
import cors from '@fastify/cors';

// Register before routes
await server.register(cors, {
  origin: true,          // reflect request origin (permissive — appropriate for a public mint)
  methods: ['GET', 'POST', 'OPTIONS'],
  allowedHeaders: ['Content-Type', 'Authorization'],
  credentials: false,    // Cashu mints don't use credentials
});
```

**Step 3 — Add CORS origin config to src/utils/config.ts (optional but good):**
```typescript
corsOrigin: z.union([z.string(), z.boolean()]).default(true),
```
This allows operators to restrict origins in production via env var if desired.

## Acceptance Criteria

- [ ] `@fastify/cors` added to package.json dependencies
- [ ] CORS plugin registered in `src/server.ts` before route registration
- [ ] `Access-Control-Allow-Origin` header present on API responses
- [ ] OPTIONS preflight requests return 200 with correct headers
- [ ] `npm run typecheck` passes
- [ ] `npm test` passes

## Notes

_Generated from gap_analyzer (P1, effort=low). One-line fix that unblocks all browser-based wallet connections._
