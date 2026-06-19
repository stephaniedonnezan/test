# Linear title prefix helper

Adds a `Cursor researching` title marker when a Linear issue status changes to
`To Research`.

The helper accepts the Cursor automation `triggerContext` shape as well as
common Linear webhook issue update payloads. It returns an update instruction
only for status changes into `To Research` and leaves already-prefixed titles
unchanged.

```bash
python3 linear_title_prefix.py < event.json
```

Example output:

```json
{
  "action": "update_issue_title",
  "issueId": "POI-4969",
  "title": "Cursor researching: Unexpected star icon when linking deliveries"
}
```
