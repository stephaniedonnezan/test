# Linear research title prefix automation

This repository contains a small webhook helper for Linear issue events.

When an issue status-change event moves to **To Research**, the helper returns an
`update_issue_title` action that prefixes the issue title with
`Cursor researching`.

```json
{
  "action": "update_issue_title",
  "issueId": "POI-4579",
  "title": "Cursor researching: MB export corrections"
}
```

The handler is side-effect free; callers are responsible for applying the
returned action to Linear.

## Usage

```python
from linear_title_prefix import build_issue_title_update

action = build_issue_title_update(linear_event)
```

The module can also be used as a CLI that reads the event JSON from stdin and
prints the action JSON when a title update is needed.

```bash
python3 -m linear_title_prefix < event.json
```

## Tests

```bash
python3 -m unittest -v
```
