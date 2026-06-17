# Linear research title prefix automation

This repository contains a small handler for Linear issue status-change
automation events. When an issue status changes to `To Research`, the handler
returns an action that prefixes the issue title with `Cursor researching`.

```python
from linear_title_prefix import build_issue_title_update

action = build_issue_title_update(event)
```

For a matching event, the returned action has this shape:

```json
{
  "action": "update_issue_title",
  "issueId": "POI-5002",
  "title": "Cursor researching: PPA supply can be checked as RFNBO in settings"
}
```

Non-status-change events, status changes to any other status, missing issue data,
and titles that already start with `Cursor researching` return `None`.

## CLI

The module can also be run as a simple JSON stdin/stdout command:

```sh
python3 linear_title_prefix.py < event.json
```

## Tests

```sh
python3 -m unittest -v
```
