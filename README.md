# Linear issue title prefix automation

This repository contains a small handler for Cursor/Linear automation payloads.
When a Linear issue status-change event moves an issue to `to research`, the
handler returns an issue-title update that prefixes the title with
`Cursor researching`.

## Usage

Pass a JSON payload on stdin:

```sh
python3 linear_title_prefix.py < payload.json
```

For matching payloads, the script prints:

```json
{"action": "update_issue_title", "issueId": "POI-4971", "title": "Cursor researching: E-mail verification after account setup"}
```

For non-matching payloads, the script exits successfully without output.

## Tests

```sh
python3 -m unittest -v
```
