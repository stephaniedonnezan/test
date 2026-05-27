# Linear issue title prefix automation

Adds `Cursor researching` to a Linear issue title when an issue status changes
to `to research`.

The automation entrypoint is `build_issue_title_update(event)` in
`linear_title_prefix.py`. It returns an action object for matching status
changes and `None` for events that should not update the issue title.

```python
{
    "action": "update_issue_title",
    "issueId": "POI-4728",
    "title": "Cursor researching: CO2 mass balance, monthly carry with RFNBO",
}
```

The module can also be used as a small CLI that reads a JSON event from stdin
and prints the action JSON.
