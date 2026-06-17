# Linear title-prefix automation

Adds a `Cursor researching` prefix to a Linear issue title when a status-change
event moves the issue to `to research`.

## Usage

Use `build_issue_title_update(event)` from `linear_title_prefix.py` with a Cursor
or Linear webhook payload. It returns an update action when the issue should be
renamed:

```python
{
    "action": "update_issue_title",
    "issueId": "POI-4934",
    "title": "Cursor researching: Issues panel must be visible across all tabs",
}
```

Non-status changes, statuses other than `to research`, missing issue data, and
titles that already start with `Cursor researching` return `None`.

The module can also be used as a small stdin/stdout CLI:

```bash
python3 linear_title_prefix.py < event.json
```

## Tests

```bash
python3 -m unittest -v
```
