# Linear issue title prefix automation

This repository contains a small handler for Linear status-change automation
events. When an issue moves to `to research`, the handler returns an action to
prefix the issue title with `Cursor researching`.

```python
from linear_title_prefix import build_issue_title_update

action = build_issue_title_update(event)
```

For matching events, the action has this shape:

```json
{
  "action": "update_issue_title",
  "issueId": "POI-4953",
  "title": "Cursor researching: Impressum + privacy policy (DE/EN)"
}
```

The handler accepts flat Cursor automation payloads and common nested Linear
webhook payloads, normalizes casing/separators, and avoids adding the prefix
when the title already starts with `Cursor researching`.

Run tests with:

```sh
python3 -m unittest -v
```
