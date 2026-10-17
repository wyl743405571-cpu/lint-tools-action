# Lint Code-Aware Check (GitHub Action)

A GitHub Action that runs **code-aware grammar** and **CWE-cited security** scans on
your pull requests — the fix for *"Grammarly breaks my code"*.

- 🧠 **Code-aware grammar**: fixes prose in comments, docs and strings without
  flagging `async/await`, identifiers, paths or technical terms as errors.
- 🛡️ **Security scan**: deterministic CWE rule pack (SQLi, XSS, secrets, command
  injection…) with cited findings. Your code is analyzed, never stored.
- 💬 Posts a PR comment with the results. Optional `fail_on_findings`.
- 🔑 Uses your own AiCredits API key (BYOK) — no shared quota.

## Why this exists

Grammarly and friends reformat code. Lint was built for developers: the grammar
engine is trained to leave code alone. This Action brings that check into CI, where
the demand actually lives.

## Usage

1. Create an API key at [aicreditsapi.com](https://aicreditsapi.com) (any paid plan).
2. Add it as a repo/org **secret** named `LINT_API_KEY`.
3. Add the workflow below.

```yaml
# .github/workflows/lint.yml
name: Lint
on: [pull_request]
jobs:
  lint:
    runs-on: ubuntu-latest
    permissions:
      pull-requests: write
      contents: read
    steps:
      - uses: actions/checkout@v4
      - uses: wyl743405571-cpu/lint-tools-action@v1
        with:
          lint_api_key: ${{ secrets.LINT_API_KEY }}
          # optional:
          # scan_paths: '**/*.py **/*.js **/*.ts'
          # check_security: 'true'
          # check_grammar: 'true'
          # fail_on_findings: 'false'
```

## Inputs

| Input | Default | Description |
|-------|---------|-------------|
| `lint_api_key` | — (required) | Your AiCredits API key (BYOK). |
| `github_token` | `${{ github.token }}` | Token for the PR comment. |
| `scan_paths` | `**/*.py **/*.js **/*.ts **/*.go **/*.rb **/*.php **/*.md` | Globs to scan. |
| `check_grammar` | `true` | Code-aware grammar/style check. |
| `check_security` | `true` | CWE security scan. |
| `fail_on_findings` | `false` | Exit non-zero on findings. |
| `max_chars` | `4000` | Max chars per file sent to the API. |

## Notes

- The Action talks to `https://tools.aicreditsapi.com`. Override with `LINT_API_BASE`
  if you self-host.
- Files over `max_chars` are truncated before sending.
- Up to 50 files per run are scanned.
