# Linear issue title research prefix

This repository contains a small handler for the Cursor/Linear automation that
adds `Cursor researching` to an issue title when the issue status changes to
`to research`.

## Behavior

`build_issue_title_update(event)` returns an action object when all of these are
true:

- the payload represents an issue status change
- the new status normalizes to `to research`
- the issue has an id and title
- the title does not already start with `Cursor researching`

The returned action has this shape:

```json
{
  "action": "update_issue_title",
  "issueId": "POI-4703",
  "title": "Cursor researching: Existing issue title"
}
```

For non-matching payloads the handler returns `null`/`None`.

## Usage

```bash
python3 linear_title_prefix.py < payload.json
```

## Tests

```bash
python3 -m unittest -v
```
