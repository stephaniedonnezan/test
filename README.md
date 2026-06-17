# Linear issue title prefix automation

Builds a side-effect-free action to prefix Linear issue titles with
`Cursor researching` when an issue status changes to `To Research`.

## Usage

Pass a Linear/Cursor automation payload on stdin:

```bash
python3 linear_title_prefix.py < payload.json
```

Matching events print an `update_issue_title` action:

```json
{
  "action": "update_issue_title",
  "issueId": "POI-4956",
  "title": "Cursor researching: Validate generated CSV against a live/sandbox Nabisy import"
}
```

Non-matching events print `null`.

## Tests

```bash
python3 -m unittest -v
```
