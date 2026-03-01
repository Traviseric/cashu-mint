# FEATURE_AUDIT TASK

**EXECUTE IMMEDIATELY** - This is an autonomous task. Don't ask questions.

You are running a Feature Audit for project **cashu-mint**.
Your job: discover what features this project claims to have, then verify if they're actually implemented.

## Step 1: Run production-audit's AI_FEATURES box (if available)

Check if production-audit exists at the path from env var `PRODUCTION_AUDIT_PATH` or the
default `C:/code/production-audit`. If it exists:

```bash
cd $PRODUCTION_AUDIT_PATH
python -m boxes.ai_features --project "C:/code/te-btc/cashu-mint" --mode deep --output "C:/code/te-btc/cashu-mint/.overnight/feature_audit_raw.json"
```

If that fails (not installed, import error, missing deps), **do the audit yourself**:
1. Discover feature claims — read README.md, landing page code, docs/, specs/, ROADMAP.md,
   package.json description, pyproject.toml metadata, or any marketing/product docs
2. For each claimed feature, search the codebase for actual implementation
3. Classify each: complete, partial, stub, mock, missing
4. Check if the feature has tests (unit, integration, or E2E)

## Step 2: Read the output

Read the raw output JSON from Step 1 (or your own analysis).

## Step 3: Write orchestrator-format output

Write this JSON to `C:/code/te-btc/cashu-mint/.overnight/feature_audit_output.json`:

```json
{
  "success": true,
  "next_box": "CONDUCTOR",
  "context": {
    "audit_type": "feature",
    "features_discovered": <number>,
    "features_verified": <number>,
    "features_complete": <number>,
    "features_partial": <number>,
    "features_missing": <number>,
    "features_stub": <number>,
    "coverage_pct": <0-100>,
    "findings": [
      {
        "severity": "critical|high|medium|low",
        "category": "feature-missing|feature-stub|feature-partial|feature-mock|feature-untested",
        "description": "<what's wrong>",
        "recommendation": "<how to fix>",
        "feature_name": "<name of the feature>",
        "effort": "low|medium|high"
      }
    ],
    "summary": "<one paragraph assessment of feature completeness>"
  }
}
```

Severity mapping:
- **critical**: Feature claimed but completely missing (misleading users)
- **high**: Feature exists but is a stub/mock (fake implementation)
- **medium**: Feature partially implemented (incomplete flows)
- **low**: Feature works but has no tests

PROJECT: cashu-mint
PATH: C:\code\te-btc\cashu-mint
RELAY DIR: C:\code\te-btc\cashu-mint\.overnight
