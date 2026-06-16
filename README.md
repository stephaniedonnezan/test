# Linear research title prefix automation

This repository contains a small, side-effect-free handler for Linear issue
webhooks. When an issue status changes to `to research`, it returns the title
update action needed to prefix the issue title with `Cursor researching`.

## Behavior

`build_issue_title_update(event)` returns:

```json
{
  "action": "update_issue_title",
  "issueId": "POI-4940",
  "title": "Cursor researching: Measure performance"
}
```

The handler returns `None` for unrelated webhook events, non-research statuses,
missing issue data, or titles that already start with `Cursor researching`
(case-insensitive).

The status and trigger checks are normalized so common variants such as
`status_changed`, `statusChanged`, `To Research`, and `to_research` are accepted.
Both flat automation payloads and nested Linear issue webhook payloads are
supported.

## CLI usage

The module can also read a JSON payload from standard input and print the update
action if one is needed:

```bash
python3 linear_title_prefix.py < payload.json
```

## Tests

Run the unit tests with:

```bash
python3 -m unittest -v
```
