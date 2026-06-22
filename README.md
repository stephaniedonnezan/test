# Linear issue title prefix automation

This repository contains a small, dependency-free helper for Linear/Cursor
automation payloads. When an issue status-change event moves an issue to
`to research`, the helper returns a declarative title-update action that adds
the `Cursor researching` prefix.

```bash
python3 linear_title_prefix.py < payload.json
```

Matching payloads print an action like:

```json
{
  "action": "update_issue_title",
  "issueId": "POI-4930",
  "title": "Cursor researching: Optimize offtaker fifo allocation"
}
```

The caller is responsible for applying the returned update with the Linear API.
