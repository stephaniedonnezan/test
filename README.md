# Linear issue title prefix automation

This repository contains a small handler for Cursor/Linear automations that
marks an issue title when the issue moves into the research workflow state.

## Behavior

`build_issue_title_update(event)` returns an update action when all of the
following are true:

- the payload represents an issue status/state change;
- the new status normalizes to `to research`;
- the issue has an id and title; and
- the title is not already prefixed with `Cursor researching`.

The returned action has this shape:

```json
{
  "action": "update_issue_title",
  "issueId": "POI-4702",
  "title": "Cursor researching: Detailed Documentation of container events"
}
```

Flat Cursor automation payloads and nested Linear webhook payloads are both
supported. Status and trigger values are normalized for case, separator, and
camel-case differences, so values such as `status_changed`, `statusChanged`,
`to_research`, `to-research`, and `ToResearch` are accepted.

## CLI

The module can also be used from stdin:

```bash
python3 linear_title_prefix.py < event.json
```

If an update is needed, the command prints the JSON action. Otherwise it exits
successfully without output.

## Tests

Run the unit tests with:

```bash
python3 -m unittest -v
```
