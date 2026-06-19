# Linear issue title prefix automation

Adds `Cursor researching` to a Linear issue title when the issue status changes
to `to research`.

## Usage

Pipe a Linear/Cursor automation event into the script:

```bash
python3 linear_title_prefix.py < event.json
```

When the event matches, the script prints an action shaped like:

```json
{
  "action": "update_issue_title",
  "issueId": "POI-4822",
  "title": "Cursor researching: Add delivery transport segment entity"
}
```

Non-matching events produce no output.

## Tests

```bash
python3 -m unittest -v
```
