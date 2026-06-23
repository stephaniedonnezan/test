# test

## Linear title prefix automation

`linear_title_prefix.py` builds a side-effect-free update action when a Linear
issue status-change payload moves to `to research`. Matching issues receive the
title prefix `Cursor researching`, while already-prefixed titles are skipped.

Run the tests with:

```bash
python3 -m unittest -v
```
