# Linear issue title prefix automation

This repository contains a small handler for Linear issue status-change events.
When an issue moves to the `to research` status, the handler builds an action to
prefix the issue title with `Cursor researching`.

## Behavior

`build_issue_title_update(event)` returns:

```json
{
  "action": "update_issue_title",
  "issueId": "POI-4826",
  "title": "Cursor researching: Existing issue title"
}
```

The handler returns `None` when:

- the event is not an issue status-change/update event
- the new status is not `to research`
- the title already starts with `Cursor researching`
- the payload does not include an issue id or title

The implementation accepts the flat Cursor automation trigger context shape as
well as common nested Linear webhook payloads.

## Verify

```sh
python3 -m unittest -v
```

## CLI

The module can also read a JSON event from stdin:

```sh
python3 linear_title_prefix.py < event.json
```
