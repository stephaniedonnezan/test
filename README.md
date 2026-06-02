# Linear issue title prefix automation

Adds a `Cursor researching` title prefix when a Linear issue status-change event
moves an issue to `to research`.

The handler exposes `build_issue_title_update(event)`, which returns an
`update_issue_title` action or `None` when the event should be ignored.

```bash
python3 linear_title_prefix.py < event.json
```
