# Linear issue title prefix automation

Builds an `update_issue_title` action when a Linear issue status changes to
`to research`, adding `Cursor researching` to the start of the title.

## Usage

```bash
python3 linear_title_prefix.py < event.json
```

For matching events, the command prints:

```json
{
  "action": "update_issue_title",
  "issueId": "POI-5107",
  "title": "Cursor researching: Existing issue title"
}
```

Non-matching events produce no output and exit successfully.
