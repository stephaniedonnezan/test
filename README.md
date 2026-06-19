# Linear issue title prefix automation

Adds `Cursor researching` to a Linear issue title when the issue status changes
to `to research`.

## Usage

Pass a Linear/Cursor automation JSON payload on stdin:

```sh
python3 linear_title_prefix.py < payload.json
```

Matching payloads print an action like:

```json
{"action": "update_issue_title", "issueId": "POI-4076", "title": "Cursor researching: Fix failing Cypress tests on main"}
```
