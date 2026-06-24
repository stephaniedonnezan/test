# Linear issue title prefix automation

This repository contains a small, side-effect-free handler for Linear status
change automations. When an issue status changes to `to research`, the handler
returns an action to prefix the issue title with `Cursor researching`.

```python
from linear_title_prefix import build_issue_title_update

update = build_issue_title_update(event)
```

For matching events, `build_issue_title_update(event)` returns:

```json
{
  "action": "update_issue_title",
  "issueId": "POI-4083",
  "title": "Cursor researching: Container Wrappers"
}
```

For non-matching events, missing issue details, or titles already beginning with
`Cursor researching`, it returns `None`.

## Local checks

Run the unit tests:

```bash
python3 -m unittest -v
```

Run the CLI with a JSON payload on stdin:

```bash
printf '%s\n' '{"trigger":"status_changed","newStatus":"to research","id":"POI-4083","title":"Container Wrappers"}' \
  | python3 linear_title_prefix.py
```
