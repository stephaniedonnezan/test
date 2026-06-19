# Linear research title prefix automation

This repository contains a small handler for Cursor/Linear automation payloads.
When an issue status changes to `to research`, `build_issue_title_update`
returns an action that prefixes the issue title with `Cursor researching`.

The handler is intentionally conservative:

- only status-change events are handled;
- generic Linear issue update events must include a status/state field change;
- status names are compared case-insensitively across common separator variants;
- existing `Cursor researching` prefixes are not duplicated.

## Usage

```bash
python3 linear_title_prefix.py < payload.json
```

For matching events, the command prints an `update_issue_title` JSON action.
For non-matching events, it exits successfully without output.

## Tests

```bash
python3 -m unittest -v
```
