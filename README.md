# mdtablefmt

Detect, format, and normalize markdown tables from the terminal.

## About

`mdtablefmt` parses Markdown documents, finds tables, and reports common formatting problems with file/line context. It can also rewrite tables into a canonical aligned form. This is useful for documentation maintenance, pre-commit checks, and reducing noisy diffs in tracked `.md` files.

## Features

- Detect common table issues: empty headers, narrow columns, and row-column mismatches.
- Rewrite tables into a stable, aligned form.
- Read from files or stdin for pipeline use.
- Plain output for terminals and markdown output for CI artifacts.
- Stdlib-only implementation with no mandatory external dependencies.

## Installation

```bash
python -m pip install -e .
```

## Usage

```bash
# Lint and report issues
mdtablefmt README.md

# Check mode for CI
mdtablefmt --check README.md

# Rewrite tables in place
mdtablefmt --in-place README.md

# Format stdin
cat README.md | mdtablefmt -

# Markdown output
mdtablefmt --format markdown README.md
```

## Exit codes

- `0` — no issues found.
- `1` — one or more table issues found.

## Project structure

```text
mdtablefmt/
  README.md
  pyproject.toml
  mdtablefmt.py
  tests/
    test_mdtablefmt.py
```

## Tags / keywords

markdown, tables, lint, format, cli, documentation, developer-tools, python
