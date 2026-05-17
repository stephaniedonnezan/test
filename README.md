# Linear issue title prefix automation

This repository contains a small handler for Linear issue status-change events.
When an issue moves to `to research`, the handler returns an action requesting
that the issue title be prefixed with `Cursor researching`.

```python
from linear_title_prefix import build_issue_title_update

update = build_issue_title_update(
    {
        "trigger": "status_changed",
        "newStatus": "to research",
        "id": "POI-4609",
        "title": "Update MB export in the audit section",
    }
)
```

The returned value is:

```json
{
  "action": "update_issue_title",
  "issueId": "POI-4609",
  "title": "Cursor researching: Update MB export in the audit section"
}
```

Non-matching events return `None`. Titles that already begin with
`Cursor researching` are left unchanged by returning `None`.

## CLI

The module can also read a JSON event from stdin and print the update action:

```sh
python3 linear_title_prefix.py < event.json
```

## Tests

```sh
python3 -m unittest -v
```
