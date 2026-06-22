# Linear issue title prefix automation

Adds `Cursor researching` to a Linear issue title when the issue status changes to
`to research`.

## Usage

Pass the Linear automation event as JSON on stdin:

```sh
python3 linear_title_prefix.py < event.json
```

When the event should update an issue, the script prints an action payload:

```json
{
  "action": "update_issue_title",
  "issueId": "POI-5073",
  "title": "Cursor researching: Backend e2e to test scenarios is escapable by user"
}
```

Events that are not status changes to `to research`, or titles that already begin
with `Cursor researching`, produce no output.

## Tests

```sh
python3 -m unittest -v
```
