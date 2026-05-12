"""Build title updates for Linear issues entering the research status."""

from __future__ import annotations

import json
import re
import sys
from collections.abc import Iterable, Mapping
from typing import Any


TITLE_PREFIX = "Cursor researching"
TARGET_STATUS = "to research"

_CAMEL_BOUNDARY = re.compile(r"(?<=[a-z0-9])(?=[A-Z])")
_SEPARATORS = re.compile(r"[^a-z0-9]+")


def build_issue_title_update(event: Mapping[str, Any]) -> dict[str, str] | None:
    """Return a Linear issue title update action when the payload qualifies.

    The automation trigger sends a compact ``triggerContext`` payload, while
    Linear webhooks can nest issue data under ``data.issue``. This function
    accepts both shapes and returns a serializable action for the caller to
    apply.
    """

    if not isinstance(event, Mapping):
        return None

    if not _is_status_change(event):
        return None

    new_status = _extract_new_status(event)
    if _normalize_token(new_status) != TARGET_STATUS:
        return None

    issue_id = _extract_issue_field(event, ("id", "issueId", "issue_id", "identifier"))
    title = _extract_issue_field(event, ("title",))
    if issue_id is None or title is None:
        return None

    issue_id = issue_id.strip()
    title = title.strip()
    if not issue_id or not title:
        return None

    if title.casefold().startswith(TITLE_PREFIX.casefold()):
        return None

    return {
        "action": "update_issue_title",
        "issueId": issue_id,
        "title": f"{TITLE_PREFIX}: {title}",
    }


def _is_status_change(event: Mapping[str, Any]) -> bool:
    for container in _iter_metadata_containers(event):
        for key in ("trigger", "webhookType", "action", "type"):
            value = container.get(key)
            normalized = _normalize_token(value)
            if normalized in {"status changed", "status change", "status updated"}:
                return True
            if normalized in {"issue updated", "updated issue", "update", "updated"}:
                return _updated_fields_include_status(event)

    return _updated_fields_include_status(event)


def _updated_fields_include_status(event: Mapping[str, Any]) -> bool:
    status_fields = {"status", "state", "workflow state", "workflowstate"}
    for container in _iter_metadata_containers(event):
        for key in ("updatedFields", "updated_fields", "changedFields", "changed_fields"):
            fields = container.get(key)
            if isinstance(fields, str):
                values: Iterable[Any] = (fields,)
            elif isinstance(fields, Iterable) and not isinstance(fields, (bytes, Mapping)):
                values = fields
            else:
                continue

            for field in values:
                if _normalize_token(field) in status_fields:
                    return True

    return False


def _extract_new_status(event: Mapping[str, Any]) -> str | None:
    direct_keys = ("newStatus", "new_status", "status", "statusName", "status_name")
    for container in _iter_issue_containers(event):
        value = _first_string(container, direct_keys)
        if value is not None:
            return value

    for container in _iter_issue_containers(event):
        for key in ("state", "status", "workflowState", "workflow_state"):
            nested = container.get(key)
            if isinstance(nested, Mapping):
                value = _first_string(nested, ("name", "title"))
                if value is not None:
                    return value

    return None


def _extract_issue_field(event: Mapping[str, Any], keys: tuple[str, ...]) -> str | None:
    for container in _iter_issue_containers(event):
        value = _first_string(container, keys)
        if value is not None:
            return value
    return None


def _first_string(container: Mapping[str, Any], keys: tuple[str, ...]) -> str | None:
    for key in keys:
        value = container.get(key)
        if isinstance(value, str):
            return value
    return None


def _iter_issue_containers(event: Mapping[str, Any]) -> Iterable[Mapping[str, Any]]:
    """Yield likely issue-bearing mappings from most specific to broadest."""

    trigger_context = event.get("triggerContext")
    if isinstance(trigger_context, Mapping):
        yield trigger_context

    data = event.get("data")
    if isinstance(data, Mapping):
        issue = data.get("issue")
        if isinstance(issue, Mapping):
            yield issue
        yield data

    issue = event.get("issue")
    if isinstance(issue, Mapping):
        yield issue

    yield event


def _iter_metadata_containers(event: Mapping[str, Any]) -> Iterable[Mapping[str, Any]]:
    yield event

    trigger_context = event.get("triggerContext")
    if isinstance(trigger_context, Mapping):
        yield trigger_context

    data = event.get("data")
    if isinstance(data, Mapping):
        yield data


def _normalize_token(value: Any) -> str:
    if not isinstance(value, str):
        return ""

    separated = _CAMEL_BOUNDARY.sub(" ", value)
    normalized = _SEPARATORS.sub(" ", separated.casefold()).strip()
    return " ".join(normalized.split())


def main() -> int:
    event = json.load(sys.stdin)
    update = build_issue_title_update(event)
    if update is not None:
        print(json.dumps(update, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
