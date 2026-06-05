# Linear issue title prefix automation

This repository contains a small, side-effect-free handler for Cursor/Linear
issue status-change automation events.

When an issue status-change payload moves to `to research`,
`build_issue_title_update(event)` returns:

```json
{
  "action": "update_issue_title",
  "issueId": "POI-4800",
  "title": "Cursor researching: []MB Grid Consumption zeros"
}
```

The handler ignores unrelated triggers, non-research statuses, and titles that
already start with `Cursor researching`.

## CLI smoke testing

The module can also be called with JSON on stdin:

```sh
python3 linear_title_prefix.py < event.json
```
