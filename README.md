# Linear research title prefix

This repository contains a small handler for Linear issue status-change
automations. When an issue moves to `to research`, it returns an action that
updates the issue title to include the `Cursor researching` prefix.

The handler ignores non-status changes, statuses other than `to research`, and
titles that already begin with the prefix.

## Usage

```bash
python3 linear_title_prefix.py < payload.json
```

## Tests

```bash
python3 -m unittest -v
```
