# Linear issue title prefix automation

Build a Linear issue title update when an issue status changes to `to research`.
The handler returns an `update_issue_title` action with the title prefixed as:

```text
Cursor researching: <original title>
```

It is side-effect free and can also be used as a stdin JSON CLI:

```sh
python3 linear_title_prefix.py < payload.json
```
