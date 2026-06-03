# Linear issue title prefix automation

Adds a `Cursor researching` prefix when a Linear issue status changes to
`to research`.

## Handler

`linear_title_prefix.build_issue_title_update(event)` accepts a Cursor
automation trigger payload or a nested Linear-style issue update payload. It
returns an update action only when all of the following are true:

- the event is a status/state/workflow-state change
- the new status normalizes to `to research`
- the issue has an id and title
- the title does not already start with `Cursor researching`

Example return value:

```json
{
  "action": "update_issue_title",
  "issueId": "POI-4809",
  "title": "Cursor researching: Reduce number of entityManager.save to one."
}
```

## CLI

The module can also read a JSON event from stdin and print the action or `null`:

```bash
python3 linear_title_prefix.py < event.json
```

## Tests

```bash
python3 -m unittest -v
```
