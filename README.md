# Linear research title automation

Adds a `Cursor researching` title prefix when a Linear issue status changes to
`to research`.

## Usage

Pipe a Cursor/Linear webhook payload into the handler:

```sh
python3 linear_title_prefix.py < payload.json
```

When the event matches, the script prints an action object:

```json
{
  "action": "update_issue_title",
  "issueId": "POI-4399",
  "title": "Cursor researching: Original issue title"
}
```

Non-matching events produce no output.
