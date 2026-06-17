# Linear title prefix helper

Adds `Cursor researching` to a Linear issue title when a status-change payload moves
the issue to `to research`.

```bash
python linear_title_prefix.py --input payload.json
```

The command prints an `updatedTitle` value when the title should change, or `null`
when the payload does not represent a matching status transition.
