# Linear title prefix automation

Adds a `Cursor researching` title prefix when a Linear issue status changes to
`to research`.

## Usage

`build_issue_title_update(event)` accepts a Cursor automation or Linear webhook
payload and returns an issue-title update action when the payload represents a
status change into `to research`:

```python
{
    "action": "update_issue_title",
    "issueId": "POI-4984",
    "title": "Cursor researching: Existing issue title",
}
```

It returns `None` for non-status triggers, other target statuses, missing
issue data, or titles that already begin with `Cursor researching`.

The module can also read a JSON event from stdin:

```bash
python3 linear_title_prefix.py < event.json
```

## Tests

```bash
python3 -m unittest -v
```
