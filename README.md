# Linear research title automation

This repository contains a small handler for Linear/Cursor automation payloads.

`build_issue_title_update(event)` returns an `update_issue_title` action when a
Linear issue status-change payload moves an issue into `to research`. The new
title is prefixed with `Cursor researching`, and existing prefixes are not
duplicated.
