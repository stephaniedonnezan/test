# test

## Linear issue title prefix

`linear_title_prefix.py` builds a Linear issue title update action when an issue
status changes to `to research`. Matching events produce:

```json
{
  "action": "update_issue_title",
  "issueId": "POI-4878",
  "title": "Cursor researching: LPH enablement even if no BOP"
}
```

The handler accepts either Cursor automation trigger contexts or nested Linear
webhook payloads on stdin:

```bash
python3 linear_title_prefix.py < payload.json
```

If the event is not a Linear issue status change to `to research`, or the title
already starts with `Cursor researching`, no output is printed.
