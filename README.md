# test

## Linear research title prefix

`linear_title_prefix.py` builds an issue-title update action when a Linear issue
status-change payload moves to `To Research`. The generated title is prefixed
with `Cursor researching: ` and already-prefixed titles are left unchanged.

Run the tests with:

```bash
python3 -m unittest -v
```
