# Linear issue title prefix automation

Adds a `Cursor researching` marker to Linear issue titles when an issue status
changes to `to research`.

## Behavior

`build_issue_title_update(event)` returns an update action only when:

- the payload represents an issue status/state/workflow-state change;
- the new status normalizes to `to research`; and
- the issue title does not already start with `Cursor researching`.

The returned action has this shape:

```json
{
  "action": "update_issue_title",
  "issueId": "POI-5047",
  "title": "Cursor researching: What is a valid default downstream emissions name?"
}
```

The helper accepts flat Cursor trigger payloads, nested `triggerContext`
payloads, and Linear-style `data.issue` payloads.

## CLI usage

Pass a JSON payload on standard input:

```sh
python3 linear_title_prefix.py < payload.json
```

If the payload should update the title, the script prints the action JSON.
Otherwise it exits successfully without output.

## Tests

```sh
python3 -m unittest -v
```
