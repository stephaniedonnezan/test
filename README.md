# Linear research title prefix

This repository contains a small automation helper for Linear issue status
changes. When an issue moves to `to research`, the helper returns an action to
prefix the title with `Cursor researching`.

Run tests with:

```sh
python3 -m unittest -v
```

Smoke-test a trigger payload with:

```sh
python3 linear_title_prefix.py < payload.json
```
