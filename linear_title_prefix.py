"""Build title update actions for Linear issue research status changes."""

from __future__ import annotations

import json
import re
import sys
from collections.abc import Iterable, Mapping
from typing import Any


RESEARCH_STATUS = "to research"
TITLE_MARKER = "Cursor researching"


def build_issue_title_update(event: Mapping[str, Any]) -> dict[str, str] | None:
    """Return an issue title update action when a Linear issue enters research."""

    if not isinstance(event, Mapping):
        return None

    sources = _payload_sources(event)
    if not _is_status_change_event(sources):
        return None

    status = _find_new_status(sources)
    if _normalize_text(status) != RESEARCH_STATUS:
        return None

    issue_id = _find_issue_id(sources)
    title = _find_title(sources)
    if not issue_id or not title:
        return None

    if title.lower().startswith(TITLE_MARKER.lower()):
        return None

    return {
        "action": "update_issue_title",
        "issueId": issue_id,
        "title": f"{TITLE_MARKER}: {title}",
    }


def _payload_sources(event: Mapping[str, Any]) -> list[Mapping[str, Any]]:
    sources: list[Mapping[str, Any]] = []

    for automation_key in ("automation_trigger_info", "automationTriggerInfo"):
        automation_info = event.get(automation_key)
        if not isinstance(automation_info, Mapping):
            continue

        trigger_context = automation_info.get("triggerContext")
        if isinstance(trigger_context, Mapping):
            sources.append(trigger_context)

        sources.append(automation_info)

    trigger_context = event.get("triggerContext")
    if isinstance(trigger_context, Mapping):
        sources.append(trigger_context)

    sources.append(event)

    data = event.get("data")
    if isinstance(data, Mapping):
        sources.append(data)

        issue = data.get("issue")
        if isinstance(issue, Mapping):
            sources.append(issue)

    issue = event.get("issue")
    if isinstance(issue, Mapping):
        sources.append(issue)

    return sources


def _is_status_change_event(sources: Iterable[Mapping[str, Any]]) -> bool:
    saw_generic_issue_update = False

    for source in sources:
        for key in ("trigger", "webhookType", "action", "type"):
            signal = _normalize_text(source.get(key))
            if not signal:
                continue

            if signal in {
                "status changed",
                "state changed",
                "workflow state changed",
                "issue status changed",
                "issue state changed",
            }:
                return True

            if signal in {"update", "updated", "issue updated", "updated issue"}:
                saw_generic_issue_update = True

        if _has_status_updated_field(source):
            return True

    return saw_generic_issue_update and any(_has_status_change_details(source) for source in sources)


def _has_status_updated_field(source: Mapping[str, Any]) -> bool:
    updated_fields = source.get("updatedFields") or source.get("updated_fields")
    if isinstance(updated_fields, str):
        updated_fields = [updated_fields]

    if isinstance(updated_fields, Iterable):
        for field in updated_fields:
            if _normalize_text(field) in {"status", "state", "workflow state"}:
                return True

    return False


def _has_status_change_details(source: Mapping[str, Any]) -> bool:
    for key in ("changes", "change", "updatedFrom", "updated_from"):
        value = source.get(key)
        if isinstance(value, Mapping):
            for changed_key in value:
                if _normalize_text(changed_key) in {"status", "state", "workflow state"}:
                    return True

    return False


def _find_new_status(sources: Iterable[Mapping[str, Any]]) -> str | None:
    explicit_status_keys = (
        "newStatus",
        "new_status",
        "newStatusName",
        "new_status_name",
        "statusName",
        "status_name",
        "stateName",
        "state_name",
        "workflowStateName",
        "workflow_state_name",
    )

    for source in sources:
        status = _first_stringish(source, explicit_status_keys)
        if status:
            return status

    for source in sources:
        status = _status_from_changes(source)
        if status:
            return status

    for source in sources:
        for key in ("status", "state", "workflowState", "workflow_state"):
            status = _string_from_status_value(source.get(key))
            if status:
                return status

    return None


def _status_from_changes(source: Mapping[str, Any]) -> str | None:
    for changes_key in ("changes", "change"):
        changes = source.get(changes_key)
        if not isinstance(changes, Mapping):
            continue

        for key in ("status", "state", "workflowState", "workflow_state"):
            status = _string_from_change_value(changes.get(key))
            if status:
                return status

    return None


def _string_from_change_value(value: Any) -> str | None:
    if isinstance(value, Mapping):
        for key in ("to", "new", "after", "name"):
            result = _string_from_status_value(value.get(key))
            if result:
                return result

    return _string_from_status_value(value)


def _find_issue_id(sources: Iterable[Mapping[str, Any]]) -> str | None:
    materialized_sources = list(sources)

    for source in materialized_sources:
        issue_id = _first_stringish(source, ("issueId", "issue_id", "identifier", "key"))
        if issue_id:
            return issue_id

    for source in materialized_sources:
        issue_id = _first_stringish(source, ("id",))
        if issue_id:
            return issue_id

    return None


def _find_title(sources: Iterable[Mapping[str, Any]]) -> str | None:
    for source in sources:
        title = _first_stringish(source, ("title",))
        if title:
            return title

    return None


def _first_stringish(source: Mapping[str, Any], keys: Iterable[str]) -> str | None:
    for key in keys:
        value = source.get(key)
        if isinstance(value, str):
            normalized = value.strip()
            if normalized:
                return normalized

    return None


def _string_from_status_value(value: Any) -> str | None:
    if isinstance(value, str):
        value = value.strip()
        return value or None

    if isinstance(value, Mapping):
        return _first_stringish(value, ("name", "title", "status", "state"))

    return None


def _normalize_text(value: Any) -> str:
    if not isinstance(value, str):
        return ""

    spaced = re.sub(r"(?<=[a-z0-9])(?=[A-Z])", " ", value)
    words = re.sub(r"[^A-Za-z0-9]+", " ", spaced).strip().lower()
    return re.sub(r"\s+", " ", words)


def main() -> int:
    payload = json.load(sys.stdin)
    action = build_issue_title_update(payload)
    json.dump(action, sys.stdout, indent=2, sort_keys=True)
    sys.stdout.write("\n")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
