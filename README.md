# Linear issue title prefix automation

This repository contains a small automation helper for Linear issue webhooks.
When an issue status changes to `to research`, the helper builds an action that
prefixes the issue title with `Cursor researching`.

## Behavior

- Handles Cursor `triggerContext` payloads and nested Linear issue update
  payloads.
- Requires a status/state/workflow-state change event.
- Matches `to research` case-insensitively and accepts common separator/camel
  case variants such as `to_research`, `to-research`, and `toResearch`.
- Skips titles that already start with `Cursor researching`.

## Usage

```python
from linear_title_prefix import build_issue_title_update

update = build_issue_title_update(event)
```

For a matching payload, `update` has this shape:

```json
{
  "action": "update_issue_title",
  "issueId": "POI-4966",
  "title": "Cursor researching: Invite landing page"
}
```

For non-matching payloads, the function returns `None`.

The module can also be used as a stdin/stdout JSON command:

```sh
python3 linear_title_prefix.py < payload.json
```

## Tests

```sh
python3 -m unittest -v
```
