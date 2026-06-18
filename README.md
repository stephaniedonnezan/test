# Linear issue title prefix automation

This repository contains a small helper for Linear/Cursor automations that marks
issues as being researched by Cursor.

`build_issue_title_update(event)` returns an action shaped like:

```json
{
  "action": "update_issue_title",
  "issueId": "POI-5063",
  "title": "Cursor researching: Improve performance"
}
```

The action is returned only when:

- the event is an issue status-change event,
- the new status normalizes to `to research`, and
- the issue title does not already start with `Cursor researching`.

The helper accepts both flat Cursor `triggerContext` payloads and nested Linear
webhook payloads under `data.issue`. It can also be used as a CLI by piping JSON
to `python3 linear_title_prefix.py`.
