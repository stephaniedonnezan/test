# Linear research title prefix

Builds a title update action when a Linear issue status changes to `to research`.
Matching issues are prefixed with `Cursor researching` unless they already have
that prefix.

The handler accepts Cursor automation trigger payloads and nested Linear webhook
payloads:

```bash
python3 linear_title_prefix.py < payload.json
```

Run tests with:

```bash
python3 -m unittest -v
```
