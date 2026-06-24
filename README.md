# Linear research title automation

Adds a title update action when a Linear issue status changes to `to research`.
Matching issues receive the title prefix `Cursor researching`.

## Usage

```bash
python3 linear_title_prefix.py < event.json
```

The script prints either an `update_issue_title` action or `null`.

## Tests

```bash
python3 -m unittest -v
```
