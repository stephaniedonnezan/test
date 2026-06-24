# Linear research title prefix automation

This repository contains a small handler for Linear issue status-change
automations. When an issue is moved to the `To Research` status, the handler
returns an action that prefixes the issue title with `Cursor researching`.

## Usage

```bash
python3 linear_title_prefix.py < payload.json
```

For a status-change payload such as:

```json
{
  "triggerContext": {
    "trigger": "status_changed",
    "newStatus": "To Research",
    "id": "POI-5017",
    "title": "There seems to be a minimum value"
  }
}
```

the script prints:

```json
{
  "action": "update_issue_title",
  "issueId": "POI-5017",
  "title": "Cursor researching: There seems to be a minimum value"
}
```

If the status change is not to `To Research`, the payload is not a status
change, or the title already starts with `Cursor researching`, the handler
prints `null`.

## Tests

```bash
python3 -m unittest -v
```
