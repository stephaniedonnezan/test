# Linear research title prefix automation

This repository contains a small JSON-in/JSON-out helper for Linear issue
automation. When an issue status-change event moves an issue to `to research`,
the helper returns an action that prefixes the issue title with
`Cursor researching`.

## Usage

```bash
python3 linear_title_prefix.py < event.json
```

For a matching event, the command prints:

```json
{
  "action": "update_issue_title",
  "issueId": "POI-3765",
  "title": "Cursor researching: Refine Site Details>KPIs"
}
```

For non-matching events, it prints nothing and exits successfully.

## Behavior

- Matches status-change triggers such as `status_changed` and `statusChanged`.
- Normalizes status values like `to research`, `To_Research`, and `to-research`.
- Supports flat Cursor trigger contexts and nested Linear webhook payloads.
- Skips titles that already start with `Cursor researching`.

## Tests

```bash
python3 -m unittest -v
```
