# Linear research title prefix automation

This repository contains a small handler for Cursor/Linear issue status-change
automations. When a Linear issue moves to `to research`, the handler returns an
`update_issue_title` action that prefixes the issue title with
`Cursor researching`.

```python
from linear_title_prefix import build_issue_title_update

update = build_issue_title_update(event)
```

The handler returns `None` for unrelated events, non-research statuses, missing
issue IDs/titles, or titles that already start with `Cursor researching`.

## Local verification

```bash
python3 -m unittest -v
```

The module can also be smoke-tested as a CLI by piping a JSON payload to
`linear_title_prefix.py`; it prints either the update action or `null`.
