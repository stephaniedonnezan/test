# Linear title prefix automation

This repository contains a small handler for Linear issue status-change
automation payloads.

When an issue status changes to `to research`, `build_issue_title_update`
returns an `update_issue_title` action that prefixes the title with
`Cursor researching`. Other statuses and already-prefixed titles are ignored.

Run the tests with:

```sh
python3 -m unittest -v
```
