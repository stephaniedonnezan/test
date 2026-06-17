# Linear research title prefix automation

This repository contains the decision helper for a Linear automation that marks
issues when they move into research.

When a status-change payload moves an issue to `to research`, the helper returns
an `update_issue_title` action that prefixes the issue title with
`Cursor researching`. Other status changes, non-status events, and titles already
starting with the prefix are ignored.

## Usage

```bash
python3 linear_title_prefix.py < payload.json
```

The command prints a JSON update action when a title change is required and
prints nothing when the event should be ignored.

## Tests

```bash
python3 -m unittest -v
```
