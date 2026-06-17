# test

## Linear research title prefix helper

`linear_title_prefix.py` builds a title-update action when a Linear issue status
change moves the issue to `to research`. Matching updates add the
`Cursor researching` marker to the issue title while avoiding duplicate markers.

Run the focused tests with:

```sh
python3 -m unittest
```
