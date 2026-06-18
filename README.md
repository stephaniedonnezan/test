# Linear issue title prefix automation

This repository contains a small handler for Cursor/Linear automation events.
When a Linear issue status changes to `to research`, the handler returns an
`update_issue_title` action that prefixes the issue title with
`Cursor researching`.

```python
from linear_title_prefix import build_issue_title_update

update = build_issue_title_update(
    {
        "trigger": "status_changed",
        "newStatus": "to research",
        "id": "POI-5070",
        "title": "AssertionError: Eex-use for CO2 should be 1 or 0",
    }
)
```

The returned action is:

```json
{
  "action": "update_issue_title",
  "issueId": "POI-5070",
  "title": "Cursor researching: AssertionError: Eex-use for CO2 should be 1 or 0"
}
```

Events with other statuses or titles that already begin with
`Cursor researching` are ignored.

## Development

Run the tests with:

```bash
python3 -m unittest -v
```

The module can also read a JSON event from stdin and print the title update:

```bash
python3 linear_title_prefix.py < event.json
```
