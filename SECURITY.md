# Security Policy

## Reporting a vulnerability

Please **do not** open a public GitHub issue for security vulnerabilities.

Instead, report privately via GitHub's
[private vulnerability reporting](https://github.com/Oisix/dbt-column-lineage/security/advisories/new):
open the repository's **Security** tab → **Report a vulnerability**.

Please include reproduction steps and the affected version. Reports are
triaged by the maintainers listed in [`.github/CODEOWNERS`](.github/CODEOWNERS);
we aim to acknowledge reports within a few business days.

## Supported versions

This project follows a rolling release model: only the **latest** version
published on PyPI is supported. Please upgrade before reporting.

## Notes for operators

- **Credentials are never committed.** `.envrc` is gitignored; keep OAuth
  (`GOOGLE_CLIENT_*`), `SESSION_SECRET`, and Looker SDK secrets out of the repo
  and out of logs. In hosted deployments, inject them via your platform's secret
  manager.
- **`SESSION_SECRET`** must be a fixed value when `USE_OAUTH=true` and you run
  more than one process/instance, or signed-cookie sessions break across
  processes. See the README and `CLAUDE.md` for details.
- The app trusts the dbt artifacts (`manifest.json`/`catalog.json`) and
  `compiled_code` it parses. Only point it at projects you trust.
