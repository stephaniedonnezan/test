# Linear issue title prefix automation

This repository contains a small handler for Linear status-change automations.

When a Linear issue changes status to `To Research`, `build_issue_title_update`
returns an action to prefix the issue title with:

```text
Cursor researching: <original title>
```

The handler is side-effect free: it returns the requested title update for the
caller to apply and returns `None` for non-matching events. It also avoids adding
the prefix when the issue title already starts with `Cursor researching`.

## Usage

```bash
python3 linear_title_prefix.py < event.json
```

## Test

```bash
python3 -m unittest -v
```
