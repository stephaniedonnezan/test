# Linear research title prefix automation

Builds a Linear issue title update when an issue status changes to `To Research`.
Matching payloads produce an `update_issue_title` action with a `Cursor researching`
title prefix, while unrelated events and already-prefixed titles are ignored.

## Usage

```bash
python3 linear_title_prefix.py < payload.json
```

The script exits with status `0` and prints JSON when a title update is needed.
It exits with status `1` and no output when the payload should be ignored.

## Tests

```bash
python3 -m unittest -v
```
