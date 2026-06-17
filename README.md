# Linear issue title automation

Adds the `Cursor researching` marker to Linear issue titles when a status-change
event moves an issue to `To Research`.

The main entrypoint is `build_issue_title_update(event)` in
`linear_title_prefix.py`. It returns an update action:

```json
{
  "action": "update_issue_title",
  "issueId": "POI-4971",
  "title": "Cursor researching: E-mail verification after account setup"
}
```

For non-matching events, malformed payloads, or titles that already start with
`Cursor researching`, it returns `None`.

The module can also be used as a small CLI that reads a JSON event from stdin
and prints the action JSON when an update is required.
