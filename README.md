# Linear research title automation

This repository contains a small handler for Linear issue status-change events.
When an issue moves to `to research`, the handler returns an action to prefix
the issue title with `Cursor researching`.

```json
{
  "action": "update_issue_title",
  "issueId": "POI-4933",
  "title": "Cursor researching: Add a meter as example"
}
```

The handler is intentionally side-effect free. Automation code can call
`build_issue_title_update(event)` and apply the returned action when it is not
`None`.

## Local checks

```bash
python3 -m unittest -v
```
