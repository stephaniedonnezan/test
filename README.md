# Linear research title prefix automation

Builds a Linear issue title update when an issue status changes to `to research`.
The returned action prefixes the existing title with `Cursor researching` and
does not duplicate the prefix if it is already present.

```bash
python3 -m unittest -v
```
