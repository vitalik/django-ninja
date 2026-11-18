# AGENTS.md

Instructions for AI coding agents working on django-ninja.

## Pull requests

Before opening a PR, do all of the following.

### 1. Test

- Add or update tests in `tests/` that fail without your change and pass with it.
- Run the full suite: `uv run pytest --cov=ninja --cov-report term-missing tests`.
  Coverage must stay at **100%** (enforced by `fail_under = 100`).
- Run `make lint` (ruff format, ruff check, mypy). All checks must pass.

### 2. Security review

Review your own diff for security problems before you open the PR. Check at least:

- Input parsing and validation: can malformed or oversized input crash the app, bypass
  validation, or use up memory or CPU?
- Auth and permissions: does the change weaken or bypass any authentication, CSRF or
  permission check, or change its defaults?
- Information leaks: do error messages, OpenAPI output or the docs UI expose internals,
  secrets or data they shouldn't?
- Injection: does any user input reach SQL, HTML or templates, headers, file paths or
  `eval` without escaping?
- New dependencies: are they really needed and well maintained?

Fix what you find. Report anything left over under **Risks**.

### 3. PR description

Keep it short. A reviewer should be able to read it in under a minute. Use this
structure and nothing more:

```markdown
## What
One or two sentences: what changes and why. Link the issue (`Fixes #123`).

## How it was verified
- The tests that prove it works (name them), and what they cover.
- Any manual check (repro script, before/after output), in one line each.

## Risks
- Security review result: "no issues found" or the specific concern.
- Edge cases or behavior that could break, if any.

## Backward compatibility
"None" or a list of what changes for existing users (API, behavior, defaults,
OpenAPI schema output) and how to migrate.
```

Don't restate the diff, list every changed file, or add filler sections.
