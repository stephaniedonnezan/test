# Linear research title prefix automation

This repository contains a small handler for Linear issue status-change
automation.

When an issue status changes to `To Research`, `build_issue_title_update`
returns an action that prefixes the issue title with `Cursor researching:`.
Events that are not status changes, do not move to `To Research`, or already
have the prefix return `None`.

## Usage

```bash
python3 linear_title_prefix.py < event.json
```

The CLI prints either a JSON action such as:

```json
{
  "action": "update_issue_title",
  "issueId": "POI-4545",
  "title": "Cursor researching: [Container Logic MB] Deliveries connected to batches outside of site"
}
```

or `null` when no title update is needed.

## Tests

```bash
python3 -m unittest -v
```
