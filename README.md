# Linear issue title prefix automation

This repository contains a small handler for Linear status-change automation.

When a Linear issue moves to `to research`, the handler returns an action that
updates the issue title with the `Cursor researching` prefix:

```json
{
  "action": "update_issue_title",
  "issueId": "POI-5065",
  "title": "Cursor researching: UBA POS should not be modifiable"
}
```

The handler is intentionally dependency-free and can also be used as a stdin JSON
CLI:

```bash
python3 linear_title_prefix.py < payload.json
```

Run tests with:

```bash
python3 -m unittest -v
```
