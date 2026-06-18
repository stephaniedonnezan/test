# Linear title prefix automation

This repository contains a small helper for Linear/Cursor automations that need
to update an issue title when the issue moves into research.

## Behavior

`linear_title_prefix.build_issue_title_update(event)` returns an action like:

```json
{
  "action": "update_issue_title",
  "issueId": "POI-5043",
  "title": "Cursor researching: Existing issue title"
}
```

The action is returned only when:

- the event is a Linear issue status/state change,
- the new status normalizes to `to research`, and
- the title does not already start with `Cursor researching`.

The helper accepts the flat Cursor `triggerContext` payload shape, direct flat
payloads, and nested Linear issue update payloads. If the event should not
change the title, the helper returns `None`.

## Usage

Run the helper from Python:

```python
from linear_title_prefix import build_issue_title_update

update = build_issue_title_update(event)
```

Or pass a JSON payload on stdin:

```sh
python3 linear_title_prefix.py < payload.json
```

## Tests

```sh
python3 -m unittest -v
```
