# Linear research title prefix

This repository contains a small handler for Cursor/Linear automation payloads.
When an issue status changes to `to research`, it builds the title update needed
to prefix the issue title with `Cursor researching`.

## Behavior

`build_issue_title_update(event)` returns an update action only when:

- the payload represents a status-change event,
- the new status normalizes to `to research`,
- the issue id and title are present, and
- the title does not already start with `Cursor researching`.

Example return value:

```json
{
  "action": "update_issue_title",
  "issueId": "POI-2649",
  "title": "Cursor researching: [1000]Auditor invite/registration/confirmation process is hectic"
}
```

The handler supports flat Cursor `triggerContext` payloads and common nested
Linear webhook shapes.

## CLI

The module can read a JSON event from stdin and print the update action:

```sh
python3 linear_title_prefix.py < event.json
```

If no title update is needed, it exits successfully without output.

## Tests

Run the unit tests with:

```sh
python3 -m unittest -v
```
