# AGENTS.md

## Project Scope

- This repo is `quant-engine`, an intraday-first Python research engine powered by Backtrader.
- Prefer the documented `uv` workflow in `README.md` before adding alternate tooling.
- Keep generated run artifacts out of git unless the user explicitly asks to preserve them.

## Useful Plugins

Use these plugins first when the work fits their lane, and keep exploring newly available plugins as research, reporting, and publishing workflows grow:

- `GitHub` for repo publishing, CI, failed-run triage, PRs, and release hygiene.
- `Spreadsheets` for reviewing trade logs, optimization outputs, walk-forward results, and CSV summaries.
- `Documents` for research notes, strategy reports, and reviewer-ready methodology docs.
- `CircleCI` for CI workflow debugging if the project moves there or needs hosted pipeline triage.
- `Hugging Face` for dataset/model research or publishing research artifacts if that becomes useful.
