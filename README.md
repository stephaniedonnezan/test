# Linear research title prefix

This repository contains a small handler for the Linear issue status-change
automation. When an issue moves to `to research`, the handler builds a
structured action that adds `Cursor researching` to the issue title.

## Usage

Pass the Linear/Cursor webhook payload on stdin:

```bash
python3 linear_title_prefix.py < payload.json
```

For a matching status change, the command prints:

```json
{
  "action": "update_issue_title",
  "issueId": "POI-4772",
  "title": "Cursor researching: In the methane excel export, use 0 instead of N/A"
}
```

It prints nothing when the payload is not a status change, the destination
status is not `to research`, the issue data is incomplete, or the title already
starts with `Cursor researching`.

## Testing

```bash
python3 -m unittest -v
```
