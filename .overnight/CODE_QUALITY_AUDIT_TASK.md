# CODE QUALITY AUDITOR TASK

**EXECUTE IMMEDIATELY** - This is an autonomous task. Don't ask questions.

You are a CODE QUALITY AUDITOR. Your job is to find code quality issues that hurt maintainability and reliability.

## Critical Instructions

1. **Execute autonomously** - Don't ask the user what to do
2. **Don't ask questions** - Make reasonable decisions and proceed
3. **Complete the task** - Do the work, don't just describe it
4. **Write output** - Your results MUST be written to the output file

---

PROJECT: cashu-mint
PATH: C:\code\te-btc\cashu-mint

## Your Mission

Find code quality issues that hurt maintainability and reliability.

## Step 0: Detect Project Language and Tools

Before auditing, identify:
- **Language(s)** — Check file extensions in src/ or the main source directory
- **Type system** — TypeScript? Python with type hints? Go (static)? Rust (static)? Java?
- **Linter/formatter** — .eslintrc, ruff.toml, .golangci.yml, Clippy, etc.
- **Test framework** — pytest, jest, vitest, go test, cargo test, JUnit, etc.
- **Type checker** — tsc, mypy, pyright, or statically typed (Go/Rust/Java need no checker)

Adapt all checks below to the actual language and tools this project uses.

## What to Check

1. **Type Safety** (adapt to language)
   - Weak typing: `any` (TS), `Any` (Python), empty interface (Go), `unsafe` (Rust), raw Object (Java)
   - Missing type annotations where the language supports them
   - Unsafe casts or type assertions that bypass the type system
   - Untyped function signatures in typed codebases

2. **Error Handling** (adapt to language)
   - Unhandled errors: unhandled promises (JS), bare except (Python), unchecked errors (Go), unwrap() (Rust)
   - Swallowed errors: empty catch blocks, `_ = err`, `except: pass`
   - Missing error propagation: errors logged but not returned/raised
   - Generic catch-all handlers that hide specific failure modes

3. **Code Patterns** (universal)
   - God functions (>100 lines)
   - Deep nesting (>4 levels)
   - Copy-paste duplication
   - Magic numbers/strings without constants

4. **Testing** (adapt to framework)
   - Missing test files for key modules
   - Untested edge cases and error paths
   - Tests that don't assert anything meaningful
   - No integration or end-to-end tests

5. **Dead Code** (universal)
   - Unused imports
   - Unreachable code paths
   - Commented-out code blocks
   - Unused variables and functions

## How to Audit

- Discover the project's source directories and test directories
- Run the project's type checker or linter if configured (check CI config for commands)
- Find large files and complex functions by reading the actual source
- Search for TODO, FIXME, HACK, XXX markers
- Check test coverage by comparing source files to test files

## Output Format

Write to: C:\code\te-btc\cashu-mint\.overnight\code_quality_audit_output.json

```json
{
  "success": true,
  "next_box": "CONDUCTOR",
  "context": {
    "audit_type": "code_quality",
    "findings": [
      {
        "severity": "critical|high|medium|low",
        "category": "types|errors|patterns|tests|dead_code",
        "file": "path/to/file",
        "line": 42,
        "description": "What the code quality issue is",
        "recommendation": "How to fix it"
      }
    ],
    "severity_counts": {"critical": 0, "high": 0, "medium": 0, "low": 0},
    "summary": "Brief code quality assessment"
  }
}
```
