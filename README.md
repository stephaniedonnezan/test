# Linear issue title prefix automation

This repository contains a small helper for Cursor automations triggered by
Linear issue status changes.

When a Linear issue status changes to `to research`, the helper returns an
`update_issue_title` action that prefixes the existing title with
`Cursor researching`.

Example input:

```json
{
  "triggerContext": {
    "trigger": "status_changed",
    "newStatus": "to research",
    "id": "POI-3398",
    "title": "Default values for incoming pos attributes of e-Methane"
  }
}
```

Example output:

```json
{
  "action": "update_issue_title",
  "issueId": "POI-3398",
  "title": "Cursor researching: Default values for incoming pos attributes of e-Methane"
}
```

The helper is side-effect free and does not call Linear directly.

## Usage

Run the CLI with a JSON event payload on stdin:

```bash
python3 linear_title_prefix.py < event.json
```

Run tests with:

```bash
python3 -m unittest -v
```
