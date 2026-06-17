# Linear issue title prefix automation

Adds a `Cursor researching` prefix to a Linear issue title when the issue moves
to the `to research` status.

## Usage

The Python module exposes `build_issue_title_update(event)`, which returns an
`update_issue_title` action for matching status-change events and `None`
otherwise.

It can also be used as a small CLI that reads a JSON event from stdin:

```sh
python3 linear_title_prefix.py < event.json
```

## Tests

```sh
python3 -m unittest -v
```
