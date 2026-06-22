# Linear issue title research prefix

This repository contains a small Linear webhook helper for Cursor automation.

`linear_title_prefix.py` reads a Linear issue status-change payload and returns an
`update_issue_title` action when the issue's new status is `To Research`.
Matching issue titles are prefixed with `Cursor researching: ` unless the title
already starts with that prefix.

## Usage

```bash
python3 linear_title_prefix.py < payload.json
```

Non-matching payloads produce no output.

## Tests

```bash
python3 -m unittest -v
```
