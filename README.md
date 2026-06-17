# Linear issue title research marker

This repository contains a small helper for Linear status-change automations.
When an issue status changes to `to research`, `linear_title_prefix.py` returns
an update action that prefixes the issue title with `Cursor researching`.

```json
{
  "action": "update_issue_title",
  "issueId": "POI-4973",
  "title": "Cursor researching: Existing issue title"
}
```

The helper is side-effect free; callers are responsible for applying the
returned action to Linear. It accepts Cursor's flat `triggerContext` payloads as
well as nested Linear issue update webhooks.

## CLI

Pass a JSON webhook payload on stdin:

```bash
python3 linear_title_prefix.py < payload.json
```

If the event should update the title, the CLI prints the JSON action. Otherwise
it exits successfully without output.

## Tests

```bash
python3 -m unittest -v
```
