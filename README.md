# Linear research status title prefix

This repository contains a small automation helper for Linear issue status-change
payloads.

When an issue status changes to `to research`, the helper returns an
`update_issue_title` action that prefixes the issue title with
`Cursor researching`. Non-matching status changes, non-status events, missing
issue data, and titles that already start with the prefix are ignored.

## Usage

The module exposes `build_issue_title_update(event)` for direct use:

```python
from linear_title_prefix import build_issue_title_update

update = build_issue_title_update(linear_event)
```

It can also be used as a CLI that reads a JSON payload from stdin:

```bash
python3 linear_title_prefix.py < payload.json
```

Matching payloads print a JSON update action. Ignored payloads exit
successfully without output.

## Testing

```bash
python3 -m unittest -v
```
