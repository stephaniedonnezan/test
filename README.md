# Linear issue title prefix automation

Adds `Cursor researching` to a Linear issue title when an issue status-change
event moves the issue to `To Research`.

The Python handler exposes:

- `build_issue_title_update(event)`
- `handle_issue_status_changed(event)`

Both return an `update_issue_title` action for matching events, or `None` when
the event should be ignored. The script can also be used as a stdin JSON CLI:

```sh
python3 linear_title_prefix.py < event.json
```

Run tests with:

```sh
python3 -m unittest -v
```
