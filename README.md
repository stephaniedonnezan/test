# Linear issue title prefix automation

This repository contains a small handler for Cursor/Linear automation payloads.
When an issue status-change event moves to `to research`, the handler returns an
action instructing the runner to prefix the issue title with `Cursor researching`.

```python
from linear_title_prefix import build_issue_title_update

update = build_issue_title_update(event)
```

For matching events, `update` has this shape:

```json
{
  "action": "update_issue_title",
  "issueId": "POI-123",
  "title": "Cursor researching: Existing issue title"
}
```

Non-matching events return `None`. Titles that already start with
`Cursor researching` are ignored to avoid duplicate prefixes.

## Tests

Run the unit tests with:

```sh
python3 -m unittest -v
```
