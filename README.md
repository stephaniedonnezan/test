# Linear issue title prefix automation

This repository contains a small handler for Cursor/Linear issue automation
payloads.

When an issue status-change event moves an issue to `to research`,
`build_issue_title_update(event)` returns an update action that prefixes the
issue title with `Cursor researching`.

```python
from linear_title_prefix import build_issue_title_update

update = build_issue_title_update(event)
```

The CLI accepts a JSON payload on stdin and prints the update action as JSON
when the payload matches:

```sh
python3 linear_title_prefix.py < payload.json
```

Run tests with:

```sh
python3 -m unittest -v
```
