# Linear issue title prefix automation

Adds `Cursor researching` to a Linear issue title when an issue status changes
to `to research`.

## Usage

Pipe a Linear/Cursor automation payload into the CLI:

```sh
python3 linear_title_prefix.py < payload.json
```

When the payload represents a matching status change, the script prints an
action object:

```json
{
  "action": "update_issue_title",
  "issueId": "POI-4043",
  "title": "Cursor researching: Adjust export generator"
}
```

No output is produced for non-matching events.
