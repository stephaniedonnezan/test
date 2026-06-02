# Linear research title prefix automation

This repository contains a small handler for Linear issue status-change
automation events. When an issue moves to `To Research`, the handler emits an
`update_issue_title` action that prefixes the issue title with
`Cursor researching`.

## Usage

```bash
python3 -m linear_title_prefix < payload.json
```

Matching payloads print JSON like:

```json
{
  "action": "update_issue_title",
  "issueId": "POI-4800",
  "title": "Cursor researching: MB Grid Consumption zeros"
}
```

Non-matching payloads produce no output.

## Tests

```bash
python3 -m unittest -v
```
