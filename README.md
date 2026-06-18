# Linear issue title prefix automation

This repository contains a small handler for Linear status-change automation.

When a Linear issue moves to `To Research`, `build_issue_title_update(event)`
returns an action that prefixes the issue title with `Cursor researching`:

```json
{
  "action": "update_issue_title",
  "issueId": "POI-5069",
  "title": "Cursor researching: Existing issue title"
}
```

Unrelated triggers, non-research statuses, missing issue data, and titles that
already begin with `Cursor researching` return `null`/`None`.

## CLI usage

The module can read a JSON payload from stdin and write the action JSON to
stdout:

```sh
python3 linear_title_prefix.py < payload.json
```

## Tests

```sh
python3 -m unittest -v
```
