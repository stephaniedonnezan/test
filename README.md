# Linear issue title prefix automation

Adds `Cursor researching` to a Linear issue title when a status-change payload
moves the issue to `to research`.

## Usage

Import `build_issue_title_update` from `linear_title_prefix.py` and pass the
automation payload. The function returns an `update_issue_title` action or
`None` when no title change is needed.

```python
from linear_title_prefix import build_issue_title_update

action = build_issue_title_update(payload)
```

For local verification, pipe a JSON payload into the module:

```bash
python3 linear_title_prefix.py < payload.json
```
