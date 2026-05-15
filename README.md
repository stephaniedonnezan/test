# Linear issue title prefix automation

Adds the `Cursor researching` title prefix when a Linear issue status changes to
`to research`.

## Usage

Pass the Linear automation payload on stdin:

```bash
python3 linear_title_prefix.py < payload.json
```

When the event qualifies, the script prints an `update_issue_title` action with
the issue id and prefixed title. Otherwise it prints `null`.

## Tests

```bash
python3 -m unittest -v
```
