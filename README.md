# Linear research title prefix automation

This repository contains a small, side-effect-free handler for Cursor/Linear
automation payloads.

When a Linear issue status changes to `to research`, `build_issue_title_update`
returns an action asking the caller to update the title to:

```text
Cursor researching: <current title>
```

Other triggers or statuses return no action.

## Usage

```bash
python3 linear_title_prefix.py < payload.json
```

## Tests

```bash
python3 -m unittest -v
```
