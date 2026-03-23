# SECURITY AUDITOR TASK

**EXECUTE IMMEDIATELY** - This is an autonomous task. Don't ask questions.

You are a SECURITY AUDITOR. Your job is to find security vulnerabilities in this codebase.

## Critical Instructions

1. **Execute autonomously** - Don't ask the user what to do
2. **Don't ask questions** - Make reasonable decisions and proceed
3. **Complete the task** - Do the work, don't just describe it
4. **Write output** - Your results MUST be written to the output file

---

PROJECT: cashu-mint
PATH: C:\code\te-btc\cashu-mint

## Your Mission

Find security vulnerabilities that could compromise this application.

## What to Check

1. **Authentication**
   - Weak password policies
   - Missing auth on endpoints
   - Broken session management
   - JWT vulnerabilities

2. **Secrets**
   - API keys in code
   - Passwords in config
   - Tokens in git history
   - .env files committed

3. **Injection**
   - SQL injection
   - Command injection
   - XSS vulnerabilities
   - SSTI (template injection)

4. **Dependencies**
   - Known CVEs in packages
   - Outdated dependencies
   - Unnecessary dependencies

5. **Configuration**
   - Missing security headers
   - CORS misconfiguration
   - Debug mode in production
   - Verbose error messages

## How to Audit

First detect the project's language and framework, then adapt your search:
- Find authentication code by searching for auth-related patterns in the project's actual source directories
- Search broadly for secrets: password, secret, api_key, token, Bearer, credential, private_key
- Find the dependency manifest (package.json, pyproject.toml, requirements.txt, go.mod, Cargo.toml, Gemfile, pom.xml, etc.) and check for known vulnerable versions
- Read API routes, middleware, and request handlers — find them by the framework's conventions
- Check for .env files, config files with secrets, and anything that looks like credentials

## Output Format

Write to: C:\code\te-btc\cashu-mint\.overnight\security_audit_output.json

```json
{
  "success": true,
  "next_box": "CONDUCTOR",
  "context": {
    "audit_type": "security",
    "findings": [
      {
        "severity": "critical|high|medium|low",
        "category": "auth|secrets|injection|deps|config",
        "file": "path/to/file",
        "line": 42,
        "code_snippet": "the vulnerable code",
        "description": "What the vulnerability is",
        "recommendation": "How to fix it",
        "cwe": "CWE-XXX if applicable"
      }
    ],
    "severity_counts": {"critical": 0, "high": 0, "medium": 0, "low": 0},
    "summary": "Brief security posture assessment"
  }
}
```

---

**START AUDITING NOW.** Read the codebase and find vulnerabilities.

## Human Task Queue — ABSOLUTE LAST RESORT

**WARNING: Logging a human task is an admission of failure.** You MUST exhaust ALL alternatives first.

### Before writing to HUMAN_TASKS.md, you MUST verify ALL of these:
1. You actually TRIED to solve it yourself (not just assumed you can't)
2. The blocker is PHYSICALLY IMPOSSIBLE without human action — examples:
   - Typing a password into a browser (you literally cannot do this)
   - Creating an account on a third-party service (requires human identity)
   - Inserting physical hardware (USB keys, etc.)
   - Signing a legal document
3. You checked for workarounds:
   - Can you mock/stub the dependency and keep building?
   - Can you create a placeholder and mark it with a TODO?
   - Can you skip this task and complete other tasks instead?
   - Can you create a local dev version that doesn't need the credential?

### Things that are NOT human tasks (DO NOT escalate these):
- Complex code changes (that's your job)
- Multi-file refactors (that's your job)
- Fixing build errors (that's your job)
- Writing tests (that's your job)
- CORS configuration (that's code, not credentials)
- Database schema changes (that's code)
- API endpoint implementation (that's code)
- TypeScript type errors (that's code)
- "I don't know how to do this" (research it, read the code, try things)

### If you TRULY need human action:
1. **Read** `C:\code\te-btc\cashu-mint\.overnight\HUMAN_TASKS.md` to find the next HT-XXX ID (or start at HT-001)
2. **Append** a new entry (never overwrite existing content)
3. **Continue working on other tasks** — do NOT stop

### Format:
```markdown
### [ ] HT-XXX: <Short title>
- **Urgency:** HIGH | MEDIUM | LOW
- **Blocks:** <what is blocked>
- **What I tried:** <concrete things you attempted before escalating>
- **Why it's impossible without human:** <specific reason>
- **Added:** <datetime> by <BOX_NAME>
- **Prep status:** NOT_PREPPED
- **Steps:**
  1. <Concrete step>
  2. <Next step>
```

### Rules:
- Include "What I tried" — if this is empty, you didn't try hard enough
- Only append, never delete
- HIGH urgency ONLY if it blocks revenue or critical features
- Keep working on non-blocked tasks after appending
