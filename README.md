# Linear research title automation

This repository contains a small Linear automation helper for issue status
changes. When an issue moves to `To Research`, the helper returns an action that
updates the issue title to start with `Cursor researching`.

The purpose of the title prefix is to make it obvious in Linear that Cursor is
actively researching the issue before implementation work begins.

## Usage

Pipe a Linear webhook or automation payload into the script:

```sh
python3 linear_title_prefix.py < payload.json
```

For matching status-change events, the script prints an update action:

```json
{"action": "update_issue_title", "issueId": "POI-4616", "title": "Cursor researching: software architecture"}
```

Non-matching events produce no output.

## Testing

```sh
python3 -m unittest -v
```
