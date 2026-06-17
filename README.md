# Linear title prefix automation

This repository contains a small handler for Linear/Cursor automation payloads.
When an issue status-change event moves an issue to `to research`, the handler
returns an action that prefixes the issue title with `Cursor researching`.

## Usage

Pass an event payload on stdin:

```sh
python3 linear_title_prefix.py < event.json
```

Matching events produce an action like:

```json
{
  "action": "update_issue_title",
  "issueId": "POI-4989",
  "title": "Cursor researching: 0 stays in Site creation Dialogue despite adding a number"
}
```

Non-matching events print `null`.

## Tests

```sh
python3 -m unittest -v
```
