# Linear issue title automation

Adds `Cursor researching` to a Linear issue title when a status-change event
moves the issue into `to research`.

## Usage

```python
from linear_title_prefix import build_issue_title_update

action = build_issue_title_update(event)
```

When the event matches, `action` is:

```json
{
  "action": "update_issue_title",
  "issueId": "POI-3478",
  "title": "Cursor researching: Let users nicely visualize"
}
```

Non-matching events return `None`.

The module can also read a JSON event from stdin and print the JSON action:

```sh
python3 linear_title_prefix.py < event.json
```

## Test

```sh
python3 -m unittest -v
```
