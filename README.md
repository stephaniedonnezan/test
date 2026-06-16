# Linear issue title prefix automation

This repository contains a small handler for Linear status-change automation.
When an issue moves to `to research`, the handler builds an action that prefixes
the issue title with `Cursor researching`.

## Usage

Pass a Linear/Cursor automation payload as JSON on stdin:

```bash
python3 linear_title_prefix.py < payload.json
```

For a qualifying status change, the script prints:

```json
{
  "action": "update_issue_title",
  "issueId": "POI-4877",
  "title": "Cursor researching: Rounding error in power allocation"
}
```

For payloads that should not update the title, the script prints `null`.

## Tests

```bash
python3 -m unittest -v
```
