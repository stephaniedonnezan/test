# Linear issue title prefix automation

This repository contains a small handler for Linear status-change automation
payloads. When an issue changes status to `to research`, the handler requests a
title update that prefixes the issue title with `Cursor researching`.

## Usage

Import `build_issue_title_update` and pass it a Linear webhook or Cursor
automation payload:

```python
from linear_title_prefix import build_issue_title_update

update = build_issue_title_update(event)
```

The function returns `None` unless the payload represents a status change to
`to research`. Matching payloads return:

```json
{
  "action": "update_issue_title",
  "issueId": "POI-123",
  "title": "Cursor researching: Existing issue title"
}
```

The handler also works as a CLI that reads JSON from stdin and prints the update
action when one is needed:

```sh
python3 linear_title_prefix.py < payload.json
```

## Tests

```sh
python3 -m unittest -v
```
