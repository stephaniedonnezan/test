# Linear issue title prefix automation

This repository contains a small handler for Cursor/Linear automations that
updates an issue title when the issue moves to the `to research` status.

## Behavior

`build_issue_title_update(event)` returns an action payload only when:

- the event is a Linear status-change event, or a generic issue update where a
  status/state field changed;
- the new status normalizes to `to research`; and
- the issue has both an id/identifier and a title.

Matching events produce:

```json
{
  "action": "update_issue_title",
  "issueId": "POI-4975",
  "title": "Cursor researching: Original title"
}
```

Titles that already start with `Cursor researching` are left unchanged so the
prefix is not duplicated.

## CLI usage

```sh
python3 linear_title_prefix.py < event.json
```

The command prints the update action as JSON for matching events and prints
nothing for events that should be ignored.

## Tests

```sh
python3 -m unittest -v
```
