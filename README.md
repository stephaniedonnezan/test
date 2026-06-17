# Linear issue title prefix automation

This repository contains a small handler for Linear issue status-change
automation payloads. When an issue moves to the `to research` status, the
handler returns an action that prefixes the issue title with
`Cursor researching`.

```python
from linear_title_prefix import build_issue_title_update

action = build_issue_title_update(event)
```

For a matching event, `build_issue_title_update` returns:

```json
{
  "action": "update_issue_title",
  "issueId": "POI-4970",
  "title": "Cursor researching: Changing from POS issuer role to User Role does not remove ability to close POSes"
}
```

Events that do not represent a status change to `to research`, or titles that
already start with `Cursor researching`, return `None`.

Run the tests with:

```sh
python3 -m unittest -v
```
