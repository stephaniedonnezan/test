# Linear research title prefix

Builds a Linear issue-title update when an issue status changes to `to research`.
The update prefixes the existing title with `Cursor researching` and skips
issues that already have that marker.

## Usage

```bash
python3 linear_title_prefix.py < event.json
```

For a matching status-change payload, the script prints an action object:

```json
{
  "action": "update_issue_title",
  "issueId": "POI-5018",
  "title": "Cursor researching: Error alert with repeating txt"
}
```

Non-matching events print `null`.

## Tests

```bash
python3 -m unittest -v
```
