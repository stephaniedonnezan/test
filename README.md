# Linear issue title prefix automation

Builds an issue-title update action when a Linear issue status changes to
`to research`.

The handler prefixes the issue title with `Cursor researching` and skips titles
that already have that prefix.

## Usage

```bash
python3 linear_title_prefix.py < payload.json
```

The module exposes `build_issue_title_update(event)` for tests and integration
code. It returns an action shaped like:

```json
{
  "action": "update_issue_title",
  "issueId": "POI-4483",
  "title": "Cursor researching: Gather ETS daily prices"
}
```
