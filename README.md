# Linear issue title prefix automation

This repository contains a small handler for Linear issue status-change events.
When an issue moves to `To Research`, the handler builds an action that prefixes
the issue title with `Cursor researching`.

## Usage

```bash
python3 linear_title_prefix.py < event.json
```

For a matching event, the command prints an action payload:

```json
{
  "action": "update_issue_title",
  "issueId": "POI-4963",
  "title": "Cursor researching: User role & rights cannot be seen by invitee"
}
```

Nonmatching events do not print anything.

## Tests

```bash
python3 -m unittest -v
```
