# Linear issue title prefix

Adds a `Cursor researching` title prefix when a Linear issue status-change event
moves the issue to `to research`.

## Usage

```python
from linear_title_prefix import build_issue_title_update

update = build_issue_title_update(event)
```

When applicable, `build_issue_title_update` returns:

```python
{
    "action": "update_issue_title",
    "issueId": "POI-4619",
    "title": "Cursor researching: Adjust global UI button",
}
```

For unsupported events, non-research statuses, missing issue data, or titles that
already start with `Cursor researching`, it returns `None`.

## Tests

```sh
python3 -m unittest -v
```
