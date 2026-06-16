# Linear issue title prefix automation

Adds `Cursor researching` to a Linear issue title when an issue status changes to
`to research`.

## Usage

Import `build_issue_title_update` and pass the Linear automation payload:

```python
from linear_title_prefix import build_issue_title_update

update = build_issue_title_update(
    {
        "trigger": "status_changed",
        "newStatus": "To Research",
        "id": "POI-4683",
        "title": "[Data Insights] three dots for every KPI box but it does nothing",
    }
)
```

When an update is needed, the function returns:

```python
{
    "action": "update_issue_title",
    "issueId": "POI-4683",
    "title": (
        "Cursor researching: "
        "[Data Insights] three dots for every KPI box but it does nothing"
    ),
}
```

It returns `None` for other status changes, non-status-change events, missing
issue details, or titles that already start with `Cursor researching`.

The module can also read JSON from stdin:

```bash
python3 linear_title_prefix.py < payload.json
```
