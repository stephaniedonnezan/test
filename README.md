# Linear research title prefix automation

This repository contains a small helper for Cursor/Linear automations. When a
Linear issue status changes to `to research`, the helper returns an action that
prefixes the issue title with `Cursor researching`.

The change is presentation-only: it produces an issue-title update action and
does not modify any saved issue data.

## Usage

Pass a JSON webhook event on stdin:

```bash
python3 linear_title_prefix.py < event.json
```

When the event is a matching status change, stdout contains:

```json
{
  "action": "update_issue_title",
  "issueId": "POI-5041",
  "title": "Cursor researching: Supply contracts are not only inputting producer"
}
```

Non-matching events exit successfully without output.

## Tests

```bash
python3 -m unittest -v
```
