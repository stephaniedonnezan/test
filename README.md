# Linear issue title research status automation

This repository contains a small handler for Linear issue status-change payloads.
When an issue moves to `to research`, it requests a title update that prefixes
the issue title with `Cursor researching`.

```python
from linear_title_prefix import build_issue_title_update

update = build_issue_title_update(
    {
        "trigger": "status_changed",
        "newStatus": "to research",
        "id": "POI-3806",
        "title": "Figure out how to handle the breakdown of certificates",
    }
)
```

The returned action is:

```json
{
  "action": "update_issue_title",
  "issueId": "POI-3806",
  "title": "Cursor researching: Figure out how to handle the breakdown of certificates"
}
```

Run tests with:

```sh
python3 -m unittest -v
```
