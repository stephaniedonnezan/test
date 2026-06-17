# Linear issue title prefix automation

This repository contains a small handler for Linear/Cursor automation events.
When an issue status changes to `To Research`, the handler returns an action to
prefix the issue title with `Cursor researching`.

```python
from linear_title_prefix import build_issue_title_update

action = build_issue_title_update(event)
```

For matching payloads, `build_issue_title_update` returns:

```json
{
  "action": "update_issue_title",
  "issueId": "POI-4962",
  "title": "Cursor researching: User role not persisiting upon invitation"
}
```

For non-matching payloads, it returns `None`. Existing `Cursor researching`
prefixes are preserved without duplication.

The module can also be used as a stdin/stdout CLI:

```bash
python3 linear_title_prefix.py < payload.json
```

## Verification

```bash
python3 -m unittest -v
```
