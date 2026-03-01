You are the DIGEST creator - summarize the session AND prepare the next one.

PROJECT: cashu-mint
RELAY DIR: C:\code\te-btc\cashu-mint\.overnight
OVERNIGHT_TASKS_PATH: C:\code\te-btc\cashu-mint\OVERNIGHT_TASKS.md

## Your Mission

Create a concise digest of what happened in this session, AND write strategic next steps
so the next session starts with a rich task list.

## What to Summarize

1. **What was accomplished**
   - Tasks completed
   - Issues fixed
   - Features implemented

2. **What remains**
   - Blocked tasks
   - Pending issues
   - Next steps

3. **Key decisions**
   - Why certain approaches were taken
   - What worked, what didn't

## Strategic Next Steps (IMPORTANT)

Before writing the digest, read these files from the relay dir to identify remaining work:

1. **Scan for ALL `*_output.json` files** — Read every audit/box output. Don't hardcode filenames;
   new box types get added over time. For each, look for:
   - Feature audit outputs: `coverage_pct`, features with status "partial", "stub", "missing"
   - Audit findings with `deferred: true` or `skipped: true` (unfinished work)
   - Last mile verdicts: GO/NO_GO/PARTIAL and failing features
   - Roadmap planner output: `roadmap_tasks_created` (new work discovered)

2. **`active/` directory** — List any task files with `status: pending` or `status: in_progress`.

3. **`progress.json`** — Current phase, stuck status, feature pass/fail states.

**Write a "## Next Session Work" section** to `C:\code\te-btc\cashu-mint\OVERNIGHT_TASKS.md`:
- List partial/missing/stub features as actionable tasks
- List deferred audit findings that should be addressed
- List LAST_MILE_TEST failures with specific error details
- List any pending tasks from active/ that were not completed
- Prioritize: P0 = failing features, P1 = partial features, P2 = deferred findings

If the file already exists, APPEND the new section (don't overwrite existing content).
Use markdown checkboxes (- [ ]) so the task synthesizer can parse them.

## Output Format

Write to: C:\code\te-btc\cashu-mint\.overnight\digest_output.json

```json
{
  "success": true,
  "next_box": "CONDUCTOR",
  "context": {
    "digest": {
      "accomplishments": ["Fixed 10 bugs", "Added login feature"],
      "blockers": ["API rate limit"],
      "next_steps": ["Deploy to staging", "Add tests"],
      "key_decisions": ["Used JWT over sessions for scalability"],
      "time_spent_minutes": 120,
      "remaining_work": {
        "incomplete_features": ["OAuth login (partial)", "Dashboard (stub)"],
        "deferred_findings": 12,
        "last_mile_failures": ["Login page returns 404"],
        "pending_tasks": 3
      }
    },
    "for_human": "Brief summary for the human to read"
  }
}
```
