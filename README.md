# Linear issue title prefix automation

Builds a Linear issue title update when an issue status changes to `To Research`.
Matching issues are prefixed with `Cursor researching` unless the title already
starts with that prefix.

## Usage

```bash
python3 linear_title_prefix.py < payload.json
```

The script prints a JSON action:

```json
{
  "action": "update_issue_title",
  "issueId": "POI-5006",
  "title": "Cursor researching: User is not warned that newly uploaded CSV file for meter reading should match the exisiting power allocation"
}
```

Run tests with:

```bash
python3 -m unittest -v
```
