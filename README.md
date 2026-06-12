# Linear research title prefix

This repository contains a small helper for Linear status-change automations. When
an issue status changes to `to research`, `linear_title_prefix.py` returns an
update action that prefixes the issue title with `Cursor researching`.

## Usage

Pipe a Linear webhook or Cursor automation event as JSON:

```sh
python3 linear_title_prefix.py < event.json
```

If the event should update the issue title, the command prints:

```json
{
  "action": "update_issue_title",
  "issueId": "POI-3324",
  "title": "Cursor researching: Create supply chain UI"
}
```

Events that do not represent a status change to `to research` produce no output.

## Tests

```sh
python3 -m unittest -v
```
