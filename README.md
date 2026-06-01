# Linear issue title prefix automation

This repository contains a small handler for Linear issue status-change
automations. When a Linear issue moves to `to research`, the handler returns an
`update_issue_title` action that prefixes the issue title with
`Cursor researching`.

## Usage

Pass a Linear automation or webhook payload as JSON on stdin:

```sh
python3 linear_title_prefix.py < payload.json
```

When the payload qualifies, the command prints JSON like:

```json
{"action": "update_issue_title", "issueId": "POI-123", "title": "Cursor researching: Original title"}
```

Non-matching payloads produce no output and exit successfully.

## Tests

```sh
python3 -m unittest -v
```
