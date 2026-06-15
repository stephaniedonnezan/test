# Linear issue title prefix automation

Adds a `Cursor researching` title prefix when a Linear issue status changes to
`To Research`.

## Usage

Call `build_issue_title_update(event)` with the Cursor/Linear webhook payload:

```python
from linear_title_prefix import build_issue_title_update

action = build_issue_title_update(event)
```

When the event represents a status change to `To Research`, the function returns:

```json
{
  "action": "update_issue_title",
  "issueId": "POI-4935",
  "title": "Cursor researching: Issues indicator is mispositioned in container logic view"
}
```

For all other events, or when the title already starts with `Cursor researching`,
the function returns `None`.

The module can also be used as a CLI that reads JSON from stdin and prints the
action JSON or `null`:

```bash
python3 linear_title_prefix.py < event.json
```

## Testing

```bash
python3 -m unittest -v
```
