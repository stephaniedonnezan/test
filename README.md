# Linear research title prefix automation

Adds a `Cursor researching` title prefix when a Linear issue status changes to
`To Research`.

## Usage

```bash
python3 linear_title_prefix.py < payload.json
```

For matching events, the command prints an `update_issue_title` action:

```json
{"action": "update_issue_title", "issueId": "POI-4581", "title": "Cursor researching: DPP of h2 crashing when you try to load it"}
```
