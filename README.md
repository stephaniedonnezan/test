# Linear research title prefix

This repository contains a small helper for Linear status-change automations.

When an issue status changes to `To Research`, `linear_title_prefix.py` builds a
side-effect-free update action that prefixes the issue title with
`Cursor researching`.

## Usage

```bash
python3 linear_title_prefix.py < event.json
```

For a matching event, the script prints:

```json
{
  "action": "update_issue_title",
  "issueId": "POI-5129",
  "title": "Cursor researching: Qualified inputs is empty for methane mb export"
}
```

If the event does not represent a status change to `To Research`, or if the
title already starts with `Cursor researching`, the script prints nothing.

## Tests

```bash
python3 -m unittest -v
```
