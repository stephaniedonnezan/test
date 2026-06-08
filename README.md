# Linear research title prefix automation

This repository contains a small helper for Linear issue status-change
automations. When an issue status changes to `to research`, the helper returns
an action instructing the caller to update the issue title with the
`Cursor researching` prefix.

## Behavior

`build_issue_title_update(event)` returns:

```json
{
  "action": "update_issue_title",
  "issueId": "POI-4837",
  "title": "Cursor researching: Existing issue title"
}
```

The function returns `None` when:

- the trigger is not a status-change event
- the new status does not normalize to `to research`
- the title already starts with `Cursor researching`
- the payload does not include both an issue id and title

The helper accepts the flat automation `triggerContext` payload shape as well
as common nested Linear webhook issue-update payloads.

## CLI

Pass a JSON payload on stdin:

```bash
python3 linear_title_prefix.py < payload.json
```

When an update is needed, the CLI prints the action JSON and exits with status
0. When no update is needed, it prints nothing and exits with status 1.

## Tests

Run the unit tests with:

```bash
python3 -m unittest -v
```
