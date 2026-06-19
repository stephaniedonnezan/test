# Linear issue title prefix automation

Adds `Cursor researching` to a Linear issue title when the issue status changes to
`to research`.

## Usage

Pass the Linear/Cursor automation payload as JSON on stdin:

```bash
python3 linear_title_prefix.py < payload.json
```

The handler prints an `update_issue_title` action only when the payload represents
a status change into `to research`.

## Tests

```bash
python3 -m unittest -v
```
