"""Build Linear issue title updates for research-status transitions."""

from __future__ import annotations

import json
import re
import sys
from collections.abc import Iterable, Mapping
from typing import Any


TITLE_PREFIX = "Cursor researching"
TARGET_STATUS = "to research"
UPDATE_ACTION = "update_issue_title"

_STATUS_CHANGE_TOKENS = {
    "status changed",
    "status change",
    "state changed",
    "state change",
    "workflow state changed",
    "workflow state change",
}
_UPDATE_TOKENS = {"update", "updated", "issue update", "issue updated", "updated issue"}
_STATUS_FIELD_NAMES = {"status", "state", "stateid", "workflowstate", "workflowstateid"}


def build_issue_title_update(event: Mapping[str, Any]) -> dict[str, str] | None:
    """Return a title-update action when a Linear issue enters To Research."""
    if not isinstance(event, Mapping):
        return None

    candidates = _candidate_dicts(event)
    if not _is_status_change(event):
        return None

    new_status = _first_text(
        candidates,
        (
            "newStatus",
            "new_status",
            "newStatusName",
            "new_status_name",
            "status",
            "statusName",
            "stateName",
            "workflowStateName",
        ),
    ) or _first_nested_name(candidates, ("state", "workflowState", "status"))
    if _normalize_words(new_status) != TARGET_STATUS:
        return None

    issue_id = _first_text(candidates, ("issueId", "issue_id", "identifier", "id"))
    title = _first_text(candidates, ("title",))
    if not issue_id or not title:
        return None

    title = title.strip()
    if not title or _has_research_prefix(title):
        return None

    return {
        "action": UPDATE_ACTION,
        "issueId": issue_id.strip(),
        "title": f"{TITLE_PREFIX}: {title}",
    }


def _candidate_dicts(event: Mapping[str, Any]) -> list[Mapping[str, Any]]:
    """Return payload dictionaries in issue-first lookup order."""
    candidates: list[Mapping[str, Any]] = []

    trigger_context = event.get("triggerContext")
    if isinstance(trigger_context, Mapping):
        candidates.append(trigger_context)

    data = event.get("data")
    if isinstance(data, Mapping):
        issue = data.get("issue")
        if isinstance(issue, Mapping):
            candidates.append(issue)
        candidates.append(data)

    issue = event.get("issue")
    if isinstance(issue, Mapping):
        candidates.append(issue)

    candidates.append(event)
    return candidates


def _is_status_change(event: Mapping[str, Any]) -> bool:
    for payload in _walk_mappings(event):
        for key in ("trigger", "event", "eventType", "webhookType", "action", "type"):
            token = _normalize_words(payload.get(key))
            if token in _STATUS_CHANGE_TOKENS:
                return True
            if token in _UPDATE_TOKENS and _updated_fields_include_status(payload):
                return True
    return False


def _updated_fields_include_status(payload: Mapping[str, Any]) -> bool:
    for key in ("updatedFields", "updated_fields", "changedFields", "changed_fields"):
        fields = payload.get(key)
        if isinstance(fields, Mapping):
            names: Iterable[Any] = fields.keys()
        elif isinstance(fields, Iterable) and not isinstance(fields, (str, bytes)):
            names = fields
        else:
            continue

        for name in names:
            if _normalize_field_name(name) in _STATUS_FIELD_NAMES:
                return True

    updated_from = payload.get("updatedFrom") or payload.get("updated_from")
    if isinstance(updated_from, Mapping):
        return any(_normalize_field_name(name) in _STATUS_FIELD_NAMES for name in updated_from)

    return False


def _first_text(candidates: Iterable[Mapping[str, Any]], keys: Iterable[str]) -> str | None:
    for candidate in candidates:
        for key in keys:
            value = candidate.get(key)
            if isinstance(value, str) and value.strip():
                return value
    return None


def _first_nested_name(
    candidates: Iterable[Mapping[str, Any]], keys: Iterable[str]
) -> str | None:
    for candidate in candidates:
        for key in keys:
            value = candidate.get(key)
            if isinstance(value, Mapping):
                name = value.get("name")
                if isinstance(name, str) and name.strip():
                    return name
    return None


def _walk_mappings(value: Any) -> Iterable[Mapping[str, Any]]:
    if isinstance(value, Mapping):
        yield value
        for child in value.values():
            yield from _walk_mappings(child)
    elif isinstance(value, list):
        for item in value:
            yield from _walk_mappings(item)


def _normalize_words(value: Any) -> str:
    if not isinstance(value, str):
        return ""
    value = re.sub(r"(?<=[a-z0-9])(?=[A-Z])", " ", value)
    value = re.sub(r"[^A-Za-z0-9]+", " ", value)
    return " ".join(value.casefold().split())


def _normalize_field_name(value: Any) -> str:
    if not isinstance(value, str):
        return ""
    return re.sub(r"[^a-z0-9]", "", value.casefold())


def _has_research_prefix(title: str) -> bool:
    return title.casefold().startswith(TITLE_PREFIX.casefold())


def main() -> int:
    event = json.load(sys.stdin)
    update = build_issue_title_update(event)
    if update is not None:
        json.dump(update, sys.stdout, sort_keys=True)
        sys.stdout.write("\n")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
