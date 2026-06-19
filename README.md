# Linear research title prefix

This repository contains a small, side-effect-free handler for Linear status
change automation events.

When an issue status changes to `To Research`, the handler returns an action to
prefix the issue title with `Cursor researching`:

```json
{
  "action": "update_issue_title",
  "issueId": "POI-4971",
  "title": "Cursor researching: E-mail verification after account setup"
}
```

The handler ignores non-status changes, statuses other than `To Research`, and
titles that already start with `Cursor researching`.

## Usage

```bash
python3 linear_title_prefix.py < payload.json
```

## Tests

```bash
python3 -m unittest -v
```
