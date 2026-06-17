# Linear issue title prefix automation

This repository contains a small, side-effect-free helper for Linear automation
events. When an issue status changes to `to research`, the helper returns an
action instructing the caller to prefix the issue title with `Cursor researching`.

```json
{
  "action": "update_issue_title",
  "issueId": "POI-5008",
  "title": "Cursor researching: is the deliveries table discoverable?"
}
```

The handler is idempotent: titles that already begin with `Cursor researching`
are left unchanged.

## Usage

```bash
python3 linear_title_prefix.py < event.json
```

## Tests

```bash
python3 -m unittest -v
```
