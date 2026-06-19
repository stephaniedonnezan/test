# Linear issue title prefix automation

Adds a `Cursor researching` prefix to Linear issue titles when an issue status
changes to `to research`.

## Handler

Use `build_issue_title_update(event)` from `linear_title_prefix.py`. It returns
an update action when the payload represents a status change to `to research`:

```python
{
    "action": "update_issue_title",
    "issueId": "POI-3610",
    "title": "Cursor researching: Create a function",
}
```

The handler returns `None` for other statuses, non-status update events, missing
issue data, or titles already prefixed with `Cursor researching`.

## Tests

```bash
python3 -m unittest -v
```
