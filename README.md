# Linear issue title prefix

This repository contains a small helper for Cursor automations that respond to
Linear issue status changes.

When a Linear issue moves to `to research`, `linear_title_prefix.py` builds an
issue-title update action that prefixes the current title with:

```text
Cursor researching:
```

The helper is idempotent: it does not emit an update when the title already
starts with `Cursor researching`.

## Usage

Pass the Linear webhook or Cursor automation event as JSON on stdin:

```bash
python3 linear_title_prefix.py < event.json
```

For a matching event, the script writes:

```json
{
  "action": "update_issue_title",
  "issueId": "POI-5040",
  "title": "Cursor researching: Existing title"
}
```

For non-matching events, it exits successfully without output.

## Tests

```bash
python3 -m unittest -v
```
