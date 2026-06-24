# Linear issue title prefix automation

Build a Linear issue title update action when an issue status-change payload moves
to `to research`.

The handler prefixes matching issue titles with `Cursor researching` and skips
titles that already start with that prefix.

## Usage

```bash
python3 linear_title_prefix.py < event.json
```

Matching events print JSON like:

```json
{"action": "update_issue_title", "issueId": "POI-4443", "title": "Cursor researching: Example issue"}
```

## Tests

```bash
python3 -m unittest -v
```
