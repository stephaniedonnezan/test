# Linear issue title research prefix

This repository contains a small automation helper for Linear issue status
change events. When an issue moves to **To Research**, the helper returns an
action that prefixes the issue title with `Cursor researching`.

## Usage

```bash
python3 linear_title_prefix.py < event.json
```

For matching events, the command prints an action object:

```json
{
  "action": "update_issue_title",
  "issueId": "POI-4767",
  "title": "Cursor researching: Existing title"
}
```

Events that are not status changes, do not move to `To Research`, or already
have the `Cursor researching` marker produce no output.

## Tests

```bash
python3 -m unittest -v
```
