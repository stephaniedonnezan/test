# Linear issue title research marker

Adds `Cursor researching` to a Linear issue title when an automation payload
reports that the issue status changed to `to research`.

For titles that start with an empty marker slot such as `[][Dev] - Example`,
the helper fills that slot:

```text
[Cursor researching][Dev] - Example
```

For other titles, it prefixes the title:

```text
Cursor researching - Example
```

## Usage

```bash
python3 linear_title_prefix.py --input payload.json
```

The command prints JSON:

```json
{"updatedTitle": "[Cursor researching][Dev] - Example"}
```

If the status is not `to research`, the trigger is not a status change, or the
title already contains the marker, `updatedTitle` is `null`.

## Tests

```bash
python3 -m unittest
```
