# Linear issue title prefix automation

This repository contains a small dependency-free handler for Cursor/Linear
automation payloads.

When a Linear issue status-change event moves an issue to `to research`,
`build_issue_title_update` returns an action requesting the issue title be
prefixed with `Cursor researching`.

```python
from linear_title_prefix import build_issue_title_update

action = build_issue_title_update(event)
```

For matching events, the action shape is:

```json
{
  "action": "update_issue_title",
  "issueId": "POI-5065",
  "title": "Cursor researching: UBA POS should not be modifiable"
}
```

Run the tests with:

```sh
python3 -m unittest -v
```
