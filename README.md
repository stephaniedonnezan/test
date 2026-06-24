# Linear issue title prefix automation

This repository contains a small side-effect-free handler for Linear status
change automation payloads.

When an issue status changes to `to research`, `linear_title_prefix.py` returns
an action that prefixes the issue title with `Cursor researching`:

```json
{
  "action": "update_issue_title",
  "issueId": "POI-4419",
  "title": "Cursor researching: [] error during MB download (Hy2gen)"
}
```

Events that are not status changes, do not move to `to research`, already have
the prefix, or are missing an issue id/title return no action.

## Usage

```bash
python3 linear_title_prefix.py < event.json
```

## Tests

```bash
python3 -m unittest -v
```
