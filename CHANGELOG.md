# Changelog

All notable changes to this project are documented here.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/).
Versions are derived from git tags via `setuptools_scm`; see the
[releases](https://github.com/Oisix/dbt-column-lineage/releases)
and [git tags](https://github.com/Oisix/dbt-column-lineage/tags)
for the full history prior to this file.

## [Unreleased]

### Added
- Design snapshots: `editableTableNode.data.change` (`new` | `modified` | `existing`)
  marks what a PR does to each model — a NEW / MODIFIED badge and border color per
  status, plus a legend row when any node has one. It can be set from the node header
  in edit mode. Nodes without it render as before.
- Design snapshots: nodes with `manual: false` are auto-laid out (dagre, using rendered
  sizes) on restore instead of keeping their `position`. Generated designs that could
  not know node sizes no longer overlap. Existing links (all `manual: true`) are
  restored exactly as before.
- Edit toolbar: **Auto layout** button that releases manual positions and re-arranges
  the canvas, to fix designs that were shared with overlapping tables.

### Changed
- Toggling edit mode re-runs the auto-layout for non-manual nodes, since designed
  nodes change width between edit and view mode. This includes analyzed lineage
  fetched from the API: its nodes are re-arranged on the toggle unless you dragged them.

## [0.6.7] - 2026-09-10

Bug-fix release for column lineage on non-Snowflake dialects, prompted by
#90 (reported against trino). Thanks to @pravinm-spry / @CodeWithPravinMaske
for the report and the first fix (#92).

### Fixed
- Table references in `compiled_code` now resolve against the sqlglot schema
  for non-Snowflake dialects. The schema built from `manifest`/`catalog` was
  registered upper-cased with `normalize=False`, which only matched
  Snowflake-style unquoted identifiers; on dialects whose unquoted identifiers
  fold to lowercase (trino, duckdb, postgres, ...) every lookup missed, so even
  `select id, jan from db.schema.model` produced no upstream edge, `select *`
  never expanded, and a `select *` over a join left an empty extra node. The
  schema now uses `normalize=True` with the manifest's original case, so both
  sides follow the same dialect rules (root cause behind #90).
- A column whose lineage passes through a `SELECT *, ROW_NUMBER() OVER (...) FROM x`
  dedup subquery ("latest row per key") no longer dead-ends with an empty
  `labels` set. sqlglot's lineage walk can terminate on the dedup subquery's
  own `Select` (wildcard projection) instead of an `exp.Table`; that leaf is
  now unwrapped back to its underlying table so lineage keeps resolving.
- Table labels now use `Table.name` instead of a raw f-string of `.this`, so a
  quoted identifier (e.g. `"raw_doctors"`) no longer produces a phantom node
  whose name still carries the quotes and fails to match the real dbt model.

## [0.6.6] - 2026-08-07

This is the first release since the project became company OSS: the
repository moved to the `Oisix` organization and is now public. Most of the
changes below come from the architecture and security reviews that gated
that publication.

### Security
- `/dashboards` no longer returns exception text to the client. The Looker
  handler put `str(e)` in the response `message`, which became the HTTP 500
  detail and could expose internal paths and library state; the details now
  go to the log only (CodeQL `py/stack-trace-exposure`).
- The CI workflow now declares `permissions: contents: read`, so its
  `GITHUB_TOKEN` is no longer granted the default write scopes
  (CodeQL `actions/missing-workflow-permissions`).
- CORS no longer allows every origin. `allow_origins` was `['*']` alongside
  `allow_credentials=True`, which makes Starlette reflect the caller's origin
  and would let any site read authenticated responses. The allowlist now
  defaults to `http://localhost:3000` (the frontend dev server) and is
  configurable via `CORS_ALLOW_ORIGINS`. Same-origin deployments — including
  the packaged app, which serves the built frontend itself — are unaffected.
- OAuth tokens are no longer written to the debug log: the Google token
  endpoint response (`access_token`, `refresh_token`, `id_token`) was logged
  verbatim, and the session's access token was logged on every page request.
  The former now logs only the status code and response key names.
- Forced `sharp` (an optional dependency of `next`, unused at runtime since
  the frontend is a static export) from 0.34.5 to 0.35.3 via an npm
  `overrides` entry, clearing the Dependabot alert for the libvips CVEs
  (CVE-2026-33327/33328/35590/35591). `next` still declares `^0.34.5`, so
  drop the override once it catches up.
- Bumped the transitive `brace-expansion` copies in the frontend lockfile
  again (1.1.16 → 1.1.18 and 5.0.8 → 5.0.9) for CVE-2026-14257 — the 1.x
  backport of the fix shipped after the advisory was published.
- CI now pins GitHub Actions to full commit SHAs (with the tag noted in a
  comment) instead of mutable major-version tags; Dependabot keeps the pins
  up to date via the existing `github-actions` ecosystem entry.
- Bumped the transitive `brace-expansion` copies in the frontend lockfile
  (1.1.15 → 1.1.16 and 5.0.6 → 5.0.8) to clear two high-severity Dependabot
  alerts that Dependabot could not raise PRs for (nested transitive pins).

### Added
- `.github/CODEOWNERS`: default owners for the whole repository
  (maintainer plus two co-maintainers).
- `CONTRIBUTING.md`: adopted the Developer Certificate of Origin —
  commits must be signed off (`git commit -s`).

### Changed
- `CODE_OF_CONDUCT.md`: conduct reports now go to the maintainers listed in
  `.github/CODEOWNERS` (same pattern as `SECURITY.md`) instead of a personal
  email address.
- `.gitignore`: ignore `uv.lock`. Dependencies are declared in
  `pyproject.toml`; the lockfile is a local artifact of whichever installer
  a contributor happens to use.
- The repository moved to the `Oisix` organization. Every GitHub URL in
  `pyproject.toml` (`[project.urls]`), `README.md`, `CHANGELOG.md`,
  `SECURITY.md`, and `.github/ISSUE_TEMPLATE/config.yml` now points at
  `Oisix/dbt-column-lineage`. GitHub permanently redirects the old paths,
  so existing links and clones keep working; the PyPI package name and
  install instructions are unchanged.
- `SECURITY.md`: vulnerability reports are triaged by the maintainers
  listed in `CODEOWNERS`; noted that GitHub private vulnerability reporting
  is unavailable while the repository is private — contact the `CODEOWNERS`
  maintainers directly in that case.

### Removed
- `test/.gitkeep`: obsolete — the tracked `test/unit/` suite already keeps
  the directory in existence.

## [0.6.5] - 2026-07-02

### Changed
- `SECURITY.md` now points to GitHub private vulnerability reporting only;
  the contact email address was removed there and from the package metadata
  (`authors` in `pyproject.toml`).
- README: removed the CI badge and the demo GIF embed, which do not render
  outside the repository.

## [0.6.4] - 2026-07-02

### Changed
- Maintainer contact email in `pyproject.toml`, `SECURITY.md`, and
  `CODE_OF_CONDUCT.md` switched to a personal address. PyPI package
  metadata reflects the new address from this release onward.

## [0.6.3] - 2026-06-22

### Added
- **`?export=png` deep link**: opening `/cl?...&export=png` (typically with
  `?design=`) fits the view, captures the canvas, and downloads it as a PNG
  automatically — no clipboard and no interaction needed, so a headless browser
  or CI can produce a static preview image in one step. The capture path no
  longer relies on the clipboard, so the bottom-right **Copy** button now falls
  back to a download when `ClipboardItem`/`navigator.clipboard.write` is
  unavailable (HTTP origins, some browsers) instead of just failing.

## [0.6.2] - 2026-06-12

### Added
- **UI guide** (`docs/ui-guide.md`, linked from the README): every operation on
  the lineage canvas and the CTE page, edit / design mode, deep links — plus the
  **design snapshot JSON spec** with `?design=` URL one-liners (lz-string /
  Python `lzstring`), so designs can be generated programmatically (e.g. by CI
  or an LLM agent attaching a design link to an automated dbt PR).
- CI now tests Python 3.13 and 3.14 (classifiers updated accordingly).

### Fixed
- **Edit mode: Import was a no-op on a loaded graph.** The dagre relayout
  effect read stale React Flow state and overwrote the imported snapshot with
  the previous graph. Imports (and large `?design=` restores) now keep all
  nodes, names, and columns.

### Changed
- Python dependencies are now single-sourced in `pyproject.toml`
  (`requirements.txt` removed); the Docker image installs from
  `[project.dependencies]` and no longer bundles `looker-sdk` (runtime never
  imports it — it stays in the `[looker]` extra for the offline analyzer).
- sqlglot 30.11.0 fixed UNPIVOT lineage (sqlglot#7727); the regression canary
  now asserts the fixed behavior. The phantom-CTE filter remains for
  sqlglot 30.x < 30.11 installs.

## [0.6.1] - 2026-06-11

### Changed
- Home landing page: clearer hero copy ("Column-level lineage for dbt") with a
  one-line value prop and an "Open the graph" CTA.

### Fixed
- Browser tab title typo: "dbt column linage" → "dbt column lineage".

## [0.6.0] - 2026-06-11

First release published with its runtime dependencies declared — earlier
versions (0.5.x) install without them and are effectively broken; use 0.6.0+.

### Fixed
- **Packaging: declare runtime dependencies.** `sqlglot`, `fastapi`, `uvicorn`,
  `requests`, `pytz`, `itsdangerous`, and `typer` are now listed in
  `[project.dependencies]`. Previously they lived only in `requirements.txt`, so
  `pip install dbt-column-lineage` installed the package without its
  dependencies. **Upgrade strongly recommended.**

### Added
- **Edit mode: edit existing models.** Each analysis model now has an
  **"Edit (design)"** item in its node menu (edit mode only) that converts it
  into an editable design node — name, columns, materialization, and PKs become
  editable. Column edges are preserved (handle IDs are unchanged).
- **Editable materialization type** (`table` / `view` / `incremental` /
  `snapshot` / `seed`) on design nodes, via a selector in the node header. The
  header color follows the type (matching the legend); the dashed border keeps
  signalling "editable". New nodes default to `table`. Round-trips through the
  `?design=` snapshot / Export.
- Replaced the default Next.js favicon with a lineage-themed `icon.svg`.
- `LICENSE` file (MIT) — the license was declared in metadata but the text was
  missing.
- `looker` optional extra for `looker-sdk` (only needed to run the offline
  `tools/looker_analyzer.py`; the runtime never calls the SDK).
- Project metadata: richer `description`, `keywords`, and `Homepage`/`Issues`/
  `Changelog` URLs.
- GitHub Actions CI: backend tests (Python 3.11/3.12) + frontend lint/build.
- Community docs: `CONTRIBUTING.md`, `SECURITY.md`, `CODE_OF_CONDUCT.md`, issue
  and pull-request templates.
- README demo GIF and a synthetic, warehouse-free demo project under `demo/`.
