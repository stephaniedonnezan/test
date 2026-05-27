# Linear issue title prefix automation

Builds an issue-title update action when a Linear issue status changes to
`to research`.

If the payload represents a status transition to `to research`, the handler
returns:

```json
{
  "action": "update_issue_title",
  "issueId": "POI-4756",
  "title": "Cursor researching: Existing issue title"
}
```

Events that do not change status to `to research`, already-prefixed titles, or
payloads without a usable issue id/title are ignored.

## Usage

```bash
python3 linear_title_prefix.py < payload.json
```

## Tests

```bash
python3 -m unittest -v
```
