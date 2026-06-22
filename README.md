# Linear research status title prefix

This repository contains a small handler for Linear issue status-change
automation events.

When a Linear issue moves to `to research`, the handler returns an action that
adds the `Cursor researching` prefix to the issue title:

```json
{
  "action": "update_issue_title",
  "issueId": "POI-5093",
  "title": "Cursor researching: MB export post QA updates"
}
```

No action is returned when:

- the event is not a status/state/workflow-state change
- the new status is not `to research`
- the issue title already starts with `Cursor researching`
- the payload does not include both an issue id and title

## Usage

Pass a JSON event payload on stdin:

```sh
python3 linear_title_prefix.py < event.json
```

Run tests with:

```sh
python3 -m unittest -v
```
