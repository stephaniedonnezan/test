# Linear research title prefix automation

This repository contains a small handler for Linear issue status-change
automations. When an issue moves to `to research`, the handler asks the
automation runner to prefix the issue title with `Cursor researching`.

## Usage

Import `build_issue_title_update` and pass the Linear/Cursor automation payload:

```python
from linear_title_prefix import build_issue_title_update

action = build_issue_title_update(event)
```

For matching events, the function returns:

```json
{
  "action": "update_issue_title",
  "issueId": "POI-4838",
  "title": "Cursor researching: Redesign of \"Add Input\""
}
```

For non-matching events, invalid payloads, or titles that are already prefixed,
it returns `None`.

The module can also be used as a CLI by piping a JSON payload to it:

```sh
python3 linear_title_prefix.py < payload.json
```
