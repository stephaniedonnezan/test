# Linear issue title prefix automation

This repository contains the decision logic for a Cursor/Linear automation:
when an issue status changes to `To Research`, build an update action that
prefixes the issue title with `Cursor researching`.

The module is side-effect free. It returns the action for the automation runner
to apply to Linear:

```json
{"action":"update_issue_title","issueId":"POI-3626","title":"Cursor researching: Existing title"}
```

## Usage

```bash
python3 linear_title_prefix.py < event.json
```

If no title update is needed, the command exits successfully without output.

## Testing

```bash
python3 -m unittest -v
```
