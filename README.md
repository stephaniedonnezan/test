# Linear research title prefix automation

This repository contains a small helper for Cursor/Linear automation events.

`linear_title_prefix.py` reads a Linear issue status-change payload and returns an
`update_issue_title` action when the issue moves to `to research`. The generated
title starts with `Cursor researching` and existing prefixes are preserved.

Run tests with:

```sh
python3 -m unittest -v
```
