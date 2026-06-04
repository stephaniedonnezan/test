# Linear issue title prefix automation

This repository contains a small handler for Linear issue status-change events.
When an issue moves to the `to research` status, the handler returns an action
to prefix the issue title with `Cursor researching`.

## Usage

Pass a Linear automation/webhook payload on stdin:

```sh
python3 linear_title_prefix.py < payload.json
```

For matching status-change events, the command prints an `update_issue_title`
action containing the issue id and prefixed title. Non-matching events exit with
status 1 and print no action.

## Tests

```sh
python3 -m unittest -v
```
