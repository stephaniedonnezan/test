# Linear issue title prefix automation

This repository contains a small, dependency-free handler for Cursor/Linear
automation events.

When a Linear issue status changes to `To Research`, the handler returns an
action object that asks the surrounding automation runner to prefix the issue
title with `Cursor researching`.

```json
{
  "action": "update_issue_title",
  "issueId": "POI-3943",
  "title": "Cursor researching: Feedstock-to-Nabisy-Biomasse-Code lookup table"
}
```

Events that are not status changes to `To Research`, or titles that already
start with `Cursor researching`, return `null`.

## Usage

```python
from linear_title_prefix import build_issue_title_update

update = build_issue_title_update(event)
```

The module can also be used as a CLI that reads the event JSON from stdin:

```sh
python3 linear_title_prefix.py < event.json
```

## Tests

```sh
python3 -m unittest -v
```
