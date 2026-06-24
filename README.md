# Linear research title prefix

This repository contains a small handler for Linear status-change automations.

When an issue changes status to `to research`, `build_issue_title_update` returns
an action that prefixes the issue title with `Cursor researching`. Other trigger
types, other statuses, missing issue data, and titles that already have the
prefix are ignored.

## Usage

```python
from linear_title_prefix import build_issue_title_update

update = build_issue_title_update(event)
```

The returned action has this shape:

```json
{
  "action": "update_issue_title",
  "issueId": "POI-4874",
  "title": "Cursor researching: Existing issue title"
}
```

The module can also be used as a CLI by piping a JSON event to stdin:

```sh
python3 linear_title_prefix.py < event.json
```

Run the test suite with:

```sh
python3 -m unittest -v
```
