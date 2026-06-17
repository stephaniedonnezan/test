# Linear issue title prefix automation

Adds a `Cursor researching` title prefix when a Linear issue status-change
event moves an issue into `To Research`.

## Contract

`build_issue_title_update(event)` returns an action dictionary when the title
should be updated:

```python
{
    "action": "update_issue_title",
    "issueId": "POI-5013",
    "title": "Cursor researching: Loading message goes behind Mass Balance items",
}
```

It returns `None` for all no-op cases, including:

- non-status-change triggers
- status changes to statuses other than `To Research`
- missing issue id or title
- titles already starting with `Cursor researching`

## Usage

```bash
python3 linear_title_prefix.py < event.json
```

## Tests

```bash
python3 -m unittest -v
```
