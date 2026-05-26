# Linear research title prefix

This repository contains a small handler for Linear issue status-change events.
When an issue moves to `To Research`, the handler returns an action that prefixes
the issue title with `Cursor researching`.

## Usage

Pass the Linear automation payload as JSON on stdin:

```bash
python3 linear_title_prefix.py < payload.json
```

If the payload represents an issue status change to `To Research`, the command
prints an update action:

```json
{
  "action": "update_issue_title",
  "issueId": "POI-4411",
  "title": "Cursor researching: Reset Philipps PW in 1password"
}
```

Non-matching events produce no output.

## Tests

```bash
python3 -m unittest -v
```
