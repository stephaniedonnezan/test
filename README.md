# Linear research title prefix

This repository contains a small handler for Linear issue status-change
automation events. When an issue status changes to `to research`, the handler
returns an action that prefixes the issue title with `Cursor researching`.

```bash
python3 linear_title_prefix.py < event.json
```

If the event does not represent a status change to `to research`, or if the
title already starts with `Cursor researching`, the handler prints nothing.
