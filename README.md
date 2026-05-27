# Linear research title prefix automation

Builds a Linear issue title update when an issue status changes to
`To Research`. Matching issues receive a `Cursor researching:` title prefix,
while titles that already start with that marker are left unchanged.

Run the tests with:

```sh
python3 -m unittest -v
```
