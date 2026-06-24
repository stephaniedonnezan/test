# Linear research title prefix

This repository contains a small handler for Linear status-change automations.

When an issue status changes to `To Research`, `linear_title_prefix.py` builds an
`update_issue_title` action that prefixes the issue title with:

```text
Cursor researching
```

The handler accepts both flat Cursor trigger-context payloads and nested Linear
webhook payloads. It returns `None` for other statuses, non-status changes, or
titles that already start with `Cursor researching`.

Run the tests with:

```sh
python3 -m unittest -v
```

You can smoke-check the CLI by piping a JSON payload to the module:

```sh
printf '%s\n' '{"trigger":"status_changed","newStatus":"To Research","id":"POI-1","title":"Example"}' \
  | python3 linear_title_prefix.py
```
