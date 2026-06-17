# Linear title prefix automation

Build an issue title update when a Linear issue status changes to `to research`.
The returned action prefixes the title with `Cursor researching` and skips issues
that already have that prefix.

## Usage

```bash
python3 linear_title_prefix.py < payload.json
```

The script prints an `update_issue_title` action when the payload should update
the Linear issue title; otherwise it exits without output.

## Tests

```bash
python3 -m unittest -v
```
