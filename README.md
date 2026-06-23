# Linear research title prefix automation

This repository contains a small handler for Linear issue status-change events.
When an issue moves to `to research`, the handler returns an update action that
adds `Cursor researching` to the beginning of the issue title:

```json
{
  "action": "update_issue_title",
  "issueId": "POI-5110",
  "title": "Cursor researching: 01 - processingMode column + routing flag"
}
```

The handler ignores non-status events, statuses other than `to research`, and
titles that already start with `Cursor researching`.

## Usage

```python
from linear_title_prefix import build_issue_title_update

update = build_issue_title_update(event)
```

It can also be used as a CLI that reads a JSON event from stdin and prints the
update action when one is required:

```sh
python3 linear_title_prefix.py < event.json
```

## Tests

```sh
python3 -m unittest -v
```
