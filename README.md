# test

## Linear research title prefix

`linear_title_prefix.py` builds a title-update action when a Linear issue status-change webhook moves an issue to `to research`. Matching events return:

```json
{
  "action": "update_issue_title",
  "issueId": "POI-4491",
  "title": "Cursor researching: N+1 Query"
}
```

Other events return no action. The helper can be imported with `build_issue_title_update(event)` or run as a small CLI that reads JSON from stdin.
