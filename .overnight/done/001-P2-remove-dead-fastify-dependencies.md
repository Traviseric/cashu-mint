---
id: 1
title: "Remove dead @fastify/swagger and @fastify/websocket dependencies"
priority: P2
severity: medium
status: completed
source: project_declared
file: package.json
line: 28
created: "2026-03-19T00:10:00"
execution_hint: parallel
context_group: independent
group_reason: "Standalone dependency cleanup, no file overlap with other tasks"
---

# Remove dead @fastify/swagger and @fastify/websocket dependencies

**Priority:** P2 (medium)
**Source:** project_declared (AGENT_TASKS.md)
**Location:** package.json:28-30

## Problem

`package.json` lists three dead dependencies that are never imported anywhere in `src/`:

- `@fastify/swagger` (^9.4.2)
- `@fastify/swagger-ui` (^5.2.1)
- `@fastify/websocket` (^11.0.2)

Grep confirms zero usage across all `src/` files. These bloat `node_modules`, increase install time, and add attack surface from unused transitive dependencies. The Cashu protocol is a REST-based JSON API — no Swagger UI or WebSocket support is currently needed.

**Code with issue:**
```json
"@fastify/swagger": "^9.4.2",
"@fastify/swagger-ui": "^5.2.1",
"@fastify/websocket": "^11.0.2",
```

## How to Fix

Remove the three dead entries from `package.json` dependencies:

```bash
npm uninstall @fastify/swagger @fastify/swagger-ui @fastify/websocket
```

Verify `node_modules` and `package-lock.json` are updated. Run `npm test` to confirm no tests break.

Note: `@fastify/websocket` is listed in ROADMAP as a Phase 3 placeholder — but carrying an unused dependency "for later" adds risk without benefit. It can be re-added when actually wired up.

## Acceptance Criteria

- [ ] `@fastify/swagger`, `@fastify/swagger-ui`, `@fastify/websocket` removed from package.json
- [ ] `npm install` runs clean (package-lock.json updated)
- [ ] `npm test` passes (33 unit tests)
- [ ] `npm run typecheck` passes
- [ ] No imports of removed packages anywhere in src/

## Notes

_Generated from AGENT_TASKS.md P2 pending item._
