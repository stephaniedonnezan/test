# Linear research title prefix

This repository contains a small, side-effect-free helper for Linear issue
automation. When an issue status-change event moves to `to research`, the
helper returns an action payload that prefixes the issue title with
`Cursor researching`.

```python
from linear_title_prefix import build_issue_title_update

update = build_issue_title_update(
    {
        "triggerContext": {
            "trigger": "status_changed",
            "newStatus": "to research",
            "id": "POI-3611",
            "title": "Add a Container Delivery Emission Strategy handler Strategy",
        }
    }
)

assert update == {
    "action": "update_issue_title",
    "issueId": "POI-3611",
    "title": "Cursor researching: Add a Container Delivery Emission Strategy handler Strategy",
}
```

The helper returns `None` for other statuses, non-status-change events, missing
issue data, or titles that already start with `Cursor researching`.

## CLI

The module can also read a JSON event from stdin and print the requested update:

```sh
python3 linear_title_prefix.py < event.json
```

## Tests

```sh
python3 -m unittest -v
```
