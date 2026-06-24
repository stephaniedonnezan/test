# Linear issue title prefix automation

This repository contains a small helper for Linear/Cursor automation events.
When a Linear issue status-change event moves an issue to `to research`, the
helper builds an update action that prefixes the issue title with
`Cursor researching`.

```python
from linear_title_prefix import build_issue_title_update

update = build_issue_title_update(event)
```

For a matching event, the returned payload is:

```json
{
  "action": "update_issue_title",
  "issueId": "POI-5036",
  "title": "Cursor researching: Mass Balance canvas items in delivery opacity off"
}
```

Non-matching events return `None`. Existing titles that already begin with
`Cursor researching` are returned without adding a duplicate prefix.

The module can also be used as a stdin JSON CLI:

```sh
python3 linear_title_prefix.py < event.json
```

Run tests with:

```sh
python3 -m unittest -v
```
