# Linear research title prefix

This repository contains a small, side-effect-free helper for Linear issue
status-change automations.

When an issue status change moves an issue to `to research`, the helper returns
an action payload that prefixes the issue title with `Cursor researching`:

```json
{
  "action": "update_issue_title",
  "issueId": "POI-4886",
  "title": "Cursor researching: get qualified outputs"
}
```

No action is returned for other statuses, non-status events, missing issue data,
or titles that already begin with `Cursor researching`.

## Usage

```python
from linear_title_prefix import build_issue_title_update

update = build_issue_title_update(event)
```

The module can also be used as a JSON stdin/stdout CLI:

```sh
python3 linear_title_prefix.py < event.json
```

## Tests

```sh
python3 -m unittest -v
```
