# Linear issue title prefix

This repository contains a small automation helper for Linear issue status
changes. When an issue moves to `to research`, the helper emits an
`update_issue_title` action that prefixes the issue title with
`Cursor researching`.

## Usage

Pipe a Linear/Cursor automation payload into the module:

```sh
python3 linear_title_prefix.py < payload.json
```

For matching status-change events, stdout contains JSON like:

```json
{"action": "update_issue_title", "issueId": "POI-5111", "title": "Cursor researching: Example issue"}
```

Non-matching events exit successfully without output.

## Test

```sh
python3 -m unittest -v
```
