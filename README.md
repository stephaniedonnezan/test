# Linear issue title prefix automation

Adds a `Cursor researching` prefix to Linear issue titles when an issue status
changes to `To Research`.

## Usage

Pass a Cursor automation or Linear webhook payload on stdin:

```sh
python3 linear_title_prefix.py < payload.json
```

When the payload represents a status change into `To Research`, the command
prints an `update_issue_title` action:

```json
{"action": "update_issue_title", "issueId": "POI-4737", "title": "Cursor researching: Example title"}
```
