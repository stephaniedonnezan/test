# Linear research title prefix

This repository contains a small handler for Linear issue status-change
automation. When an issue changes status to `to research`, the handler returns
an action that prefixes the issue title with `Cursor researching`.

## Behavior

`build_issue_title_update(event)` returns:

```json
{
  "action": "update_issue_title",
  "issueId": "POI-5004",
  "title": "Cursor researching: Search is not filtering all content"
}
```

The function returns `None` when:

- the event is not a status/state/workflow-state change
- the new status is not `to research`
- the issue id or title is missing
- the title already starts with `Cursor researching`

Status names are matched case-insensitively and tolerate common separators such
as `to_research`, `to-research`, and `ToResearch`.

## CLI

The module can also read a JSON event from stdin:

```sh
python3 linear_title_prefix.py < event.json
```

If the event should update the issue title, the CLI prints the JSON action.
No output is printed for no-op events.

## Tests

```sh
python3 -m unittest -v
```
