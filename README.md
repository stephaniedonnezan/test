# Linear issue title prefix automation

Adds a side-effect-free handler for Linear status-change automations.

When an issue status changes to `to research`, `build_issue_title_update`
returns an action that updates the issue title to:

```text
Cursor researching: <original title>
```

The handler ignores non-status updates, ignores other statuses, and avoids
adding the prefix when the title already starts with `Cursor researching`.

## Usage

```bash
python3 linear_title_prefix.py < event.json
```

The command prints a JSON `update_issue_title` action when the event should
change the title, and prints nothing when no update is needed.
