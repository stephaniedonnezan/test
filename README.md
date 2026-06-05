# Linear research title prefix automation

This repository contains a small handler for Cursor/Linear automations. When a
Linear issue status changes to `To Research`, the handler asks the caller to add
`Cursor researching` to the start of the issue title.

## Usage

```python
from linear_title_prefix import build_issue_title_update

action = build_issue_title_update(event)
```

For a matching status-change payload, `build_issue_title_update` returns:

```json
{
  "action": "update_issue_title",
  "issueId": "POI-4484",
  "title": "Cursor researching: Rework Container Closing Tab Flow"
}
```

For non-matching events, it returns `None`.

The module can also read a JSON event from stdin:

```sh
python3 linear_title_prefix.py < event.json
```

## Development

Run the tests with:

```sh
python3 -m unittest -v
```
