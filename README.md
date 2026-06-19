# Linear title prefix automation

Builds a Linear issue title update when an issue status changes to `to research`.
The update prefixes the title with `Cursor researching` and skips issues that
already have that prefix.

Run tests with:

```sh
python3 -m unittest -v
```
