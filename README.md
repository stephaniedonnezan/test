# Linear issue title prefix automation

This repository contains a small dependency-free handler for Cursor/Linear
automation payloads.

`linear_title_prefix.py` exposes `build_issue_title_update(event)`, which returns
an action like:

```json
{
  "action": "update_issue_title",
  "issueId": "POI-5070",
  "title": "Cursor researching: Existing issue title"
}
```

The action is only returned when an issue status-change event moves to
`to research`. Other statuses and unrelated issue updates return `None`, and
titles already starting with `Cursor researching` are left unchanged.

Run the tests with:

```sh
python3 -m unittest -v
```
