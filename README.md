# Linear issue title prefix

This repository contains a small transformer for Linear issue status-change
events. When an issue moves to `To Research`, the transformer returns an action
that updates the issue title with a `Cursor researching` prefix.

```json
{
  "action": "update_issue_title",
  "issueId": "POI-4798",
  "title": "Cursor researching: Rename the sites and org names in the methane demo to be clearer"
}
```

Events that are not status changes, do not move to `To Research`, are missing an
issue id or title, or already start with `Cursor researching` return `null`.

## Usage

Pipe a Linear automation or webhook payload to the CLI:

```sh
python3 linear_title_prefix.py < event.json
```

Run the tests with:

```sh
python3 -m unittest -v
```
