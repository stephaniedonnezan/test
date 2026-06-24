# Linear issue title prefix automation

Build a Linear issue-title update when a Cursor or Linear status-change payload
moves an issue into `to research`.

The handler prefixes the issue title with `Cursor researching` and avoids
duplicating that prefix when it is already present.

## Usage

```bash
python3 linear_title_prefix.py < event.json
```

## Tests

```bash
python3 -m unittest -v
```
