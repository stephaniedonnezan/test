# Linear issue title prefix automation

This repository contains a small handler for Linear issue status-change events.
When an issue moves to `to research`, the handler builds an update action that
prefixes the issue title with `Cursor researching`.

## Usage

```bash
python3 linear_title_prefix.py < payload.json
```

For a matching event, the command prints:

```json
{
  "action": "update_issue_title",
  "issueId": "POI-3091",
  "title": "Cursor researching: [FE] Dialog refinment"
}
```

Events that are not status changes to `to research`, or titles that already
start with `Cursor researching`, return `null`.

## Testing

```bash
python3 -m unittest -v
```
