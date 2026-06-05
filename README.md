# Linear research title prefix automation

This repository contains a small handler for Linear issue status-change
automations. When an issue moves to `to research`, `linear_title_prefix.py`
returns an `update_issue_title` action that prefixes the title with
`Cursor researching`.

Run the tests with:

```bash
python3 -m unittest -v
```

You can also pipe an automation payload to the script:

```bash
python3 linear_title_prefix.py < payload.json
```
