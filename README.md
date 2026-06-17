# Linear issue title prefix automation

Adds `Cursor researching` to a Linear issue title when an issue status-change
event moves the issue to `to research`.

The main entry point is `build_issue_title_update(event)` in
`linear_title_prefix.py`. It returns an update action for matching events:

```python
{
    "action": "update_issue_title",
    "issueId": "POI-4969",
    "title": "Cursor researching: Unexpected star icon when linking deliveries",
}
```

Unrelated triggers, status changes to other statuses, missing issue data, and
titles that already start with `Cursor researching` return `None`.

Run tests with:

```bash
python3 -m unittest -v
```
