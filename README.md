# Linear issue title prefix automation

Adds the `Cursor researching` marker to Linear issue titles when an issue status
changes to `to research`.

## Usage

Call `build_issue_title_update(event)` from `linear_title_prefix.py` with the
Cursor automation trigger context or a Linear webhook payload. Matching payloads
return an action object:

```json
{
  "action": "update_issue_title",
  "issueId": "POI-4934",
  "title": "Cursor researching: Issues panel must be visible across all tabs in container view"
}
```

Non-matching payloads return `None`. The module also supports a small CLI that
reads a JSON payload from stdin and prints the action or `null`:

```bash
python3 linear_title_prefix.py < payload.json
```

## Tests

```bash
python3 -m unittest -v
```
