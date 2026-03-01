# Full Flow Reference — Stage: unknown

## All Available Boxes

### Core Audits
- CODE_QUALITY_AUDIT — Types, patterns, tests, dead code
- SECURITY_AUDIT — Auth, secrets, injection, dependencies
- UX_AUDIT — Usability, accessibility, user flows (web/mobile only)
- MONETIZATION_AUDIT — Revenue blockers, payment integration, pricing
- FEATURE_AUDIT — Discover claimed features, verify implementation status
- REVIEW_AUDIT — Verify worker claims match actual code
- DESIGN_REVIEW — Information architecture, visual hierarchy, CTA placement
- PLATFORM_CONSTRAINTS — Browser/platform limits
- VISUAL_REGRESSION — CSS regression risks via code analysis
- SERVICE_INTEGRATION — Cross-service health

### Recommended for unknown: CODE_QUALITY_AUDIT

### Execution
- TASK_SYNTHESIZER — Create WORKER task files from audit findings
- WORKER — Execute tasks, write code
- ROADMAP_PLANNER — Find planned-but-unbuilt features from project docs

### Feature Testing
- LAST_MILE_TEST — Test real user flows in Chrome. GO/NO_GO/PARTIAL verdict.
- BROWSER_QA — Full exploratory sweep
- BROWSER_FEATURE_TEST — Feature-specific browser test

### Production
- DEPLOYER — Deploy to production/staging
- LIVE_TESTER — Post-deploy verification in Chrome

### Human Queue
- HUMAN_PREP — Prep browser tabs/forms for human tasks
- SWITCH_PROJECT — Move to next project

### PRAS Pipelines
- PRAS_SLOP — AI slop scan (~10 min)
- PRAS_SLOP_DELIBERATED — Slop + deliberation (~30 min)
- PRAS_AI_AUDIT — All AI audits + deliberation (~60 min)
- PRAS_FULL_AUDIT — Everything + deliberation (~60 min)

### MarketingOS
- MARKETINGOS_CONSULTING, MARKETINGOS_SEO, MARKETINGOS_FULL

### Escape Hatches
- HUMAN_CONTACT — Escalate to human when truly blocked
- GEMINI_RESEARCH — Fresh perspective from different model

## Available Workflows
- discover — RESEARCHER → FEATURE_AUDIT → GAP_ANALYZER
- plan_and_build — PLANNER → READINESS_GATE → TASK_SYNTHESIZER → WORKER
- audit_cycle — FEATURE_AUDIT → TASK_SYNTHESIZER → WORKER
- deep_audit — CODE_QUALITY_AUDIT → SECURITY_AUDIT → FEATURE_AUDIT → TASK_SYNTHESIZER → WORKER → REVIEW_AUDIT
- fix_and_verify — TASK_SYNTHESIZER → WORKER → LAST_MILE_TEST
- last_mile_fix_loop — LAST_MILE_TEST → TASK_SYNTHESIZER → WORKER → LAST_MILE_TEST
- ship_check — READINESS_GATE → LAST_MILE_TEST → BROWSER_QA
- quality_gate — REVIEW_AUDIT → LAST_MILE_TEST
- security_sweep — SECURITY_AUDIT → TASK_SYNTHESIZER → WORKER → SECURITY_AUDIT
- validate_claims — CLAIMS_VALIDATOR → USER_JOURNEY_TEST
- validate_claims_deep — CLAIMS_VALIDATOR → ADVERSARIAL_REVIEW → USER_JOURNEY_TEST
- reality_check — CLAIMS_VALIDATOR → PRAS_AI_AUDIT
- production_readiness — Full pipeline: truth → audit → plan → fix → verify → user test
- portfolio_triage — CLAIMS_VALIDATOR (score + tier)
- ship_or_kill — CLAIMS_VALIDATOR → USER_JOURNEY_TEST (binary go/no-go)
