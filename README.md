# Linear issue title prefix automation

This repository contains a small handler for Linear/Cursor automation events.
When an issue status changes to `to research`, it returns an action that prefixes
the issue title with `Cursor researching`.

## Usage

Pipe a JSON event into the module:

```bash
python3 linear_title_prefix.py < event.json
```

Matching events print:

```json
{
  "action": "update_issue_title",
  "issueId": "POI-2642",
  "title": "Cursor researching: Existing issue title"
}
```

Non-matching events print nothing and exit successfully.

## Tests

```bash
python3 -m unittest -v
```
