"""Build Linear issue title updates for Cursor research automation events."""

from __future__ import annotations

import json
import re
import sys
from collections.abc import Iterable, Mapping
from typing import Any


PREFIX = "Cursor researching"
TARGET_STATUS = "to research"
STATUS_FIELD_KEYS = {
    "status",
    "state",
    "workflowstate",
    "workflowstatus",
    "workflow_status",
    "workflow_state",
}
EXPLICIT_STATUS_KEYS = (
    "newStatus",
    "new_status",
    "statusName",
    "status_name",
    "stateName",
    "state_name",
    "workflowStateName",
    "workflow_state_name",
    "workflowStatusName",
    "workflow_status_name",
)
EVENT_KEYS = ("trigger", "triggerType", "webhookType", "action", "type", "event")


def build_issue_title_update(event: Mapping[str, Any] | None) -> dict[str, str] | None:
    """Return a title update action when an issue enters the to-research status.

    The returned action is intentionally side-effect free so callers can decide
    how to apply it to Linear.
    """

    if not isinstance(event, Mapping):
        return None

    contexts = _context_candidates(event)
    issue = _first_mapping(contexts, ("issue", "data.issue", "data"))

    issue_id = _string_from_paths(
        contexts,
        (
            "issueId",
            "issue_id",
            "identifier",
            "key",
            "id",
            "issue.issueId",
            "issue.issue_id",
            "issue.identifier",
            "issue.key",
            "issue.id",
            "data.issue.identifier",
            "data.issue.id",
            "data.identifier",
            "data.id",
        ),
    )
    title = _string_from_paths(
        contexts,
        (
            "title",
            "issue.title",
            "data.issue.title",
            "data.title",
        ),
    )

    if issue:
        issue_id = issue_id or _string_from_paths((issue,), ("identifier", "key", "id"))
        title = title or _string_from_paths((issue,), ("title",))

    if not issue_id or not title:
        return None

    target_status = _target_status(contexts)
    if _normalize_text(target_status) != TARGET_STATUS:
        return None

    if not _is_status_change_event(contexts):
        return None

    clean_title = title.strip()
    if _has_prefix(clean_title):
        prefixed_title = clean_title
    else:
        prefixed_title = f"{PREFIX}: {clean_title}"

    return {
        "action": "update_issue_title",
        "issueId": issue_id.strip(),
        "title": prefixed_title,
    }


def handle_issue_status_changed(event: Mapping[str, Any] | None) -> dict[str, str] | None:
    """Compatibility wrapper for automation entrypoints."""

    return build_issue_title_update(event)


def _context_candidates(event: Mapping[str, Any]) -> tuple[Mapping[str, Any], ...]:
    candidates: list[Mapping[str, Any]] = [event]

    for path in (
        "triggerContext",
        "automation_trigger_info.triggerContext",
        "automationTriggerInfo.triggerContext",
        "data",
        "data.issue",
    ):
        value = _value_at_path(event, path)
        if isinstance(value, Mapping):
            candidates.append(value)

    # Preserve order while removing duplicate object references.
    deduped: list[Mapping[str, Any]] = []
    seen: set[int] = set()
    for candidate in candidates:
        identity = id(candidate)
        if identity not in seen:
            deduped.append(candidate)
            seen.add(identity)

    return tuple(deduped)


def _first_mapping(
    contexts: Iterable[Mapping[str, Any]], paths: Iterable[str]
) -> Mapping[str, Any] | None:
    for context in contexts:
        for path in paths:
            value = _value_at_path(context, path)
            if isinstance(value, Mapping):
                return value
    return None


def _target_status(contexts: Iterable[Mapping[str, Any]]) -> str | None:
    for key in EXPLICIT_STATUS_KEYS:
        value = _string_from_paths(contexts, (key,))
        if value:
            return value

    changed_status = _changed_status(contexts)
    if changed_status:
        return changed_status

    for path in (
        "status.name",
        "state.name",
        "workflowState.name",
        "workflow_state.name",
        "workflowStatus.name",
        "workflow_status.name",
        "status",
        "state",
        "workflowState",
        "workflow_state",
        "workflowStatus",
        "workflow_status",
    ):
        value = _string_from_paths(contexts, (path,))
        if value:
            return value

    return None


def _changed_status(contexts: Iterable[Mapping[str, Any]]) -> str | None:
    for context in contexts:
        for path in ("changes", "changed", "change", "updatedFields"):
            value = _value_at_path(context, path)
            status_value = _status_from_change_value(value)
            if status_value:
                return status_value
    return None


def _status_from_change_value(value: Any) -> str | None:
    if isinstance(value, str):
        return None

    if isinstance(value, Mapping):
        for key, nested in value.items():
            if _is_status_field_name(str(key)):
                extracted = _extract_status_from_value(nested)
                if extracted:
                    return extracted
        return None

    if isinstance(value, Iterable):
        for item in value:
            if isinstance(item, str) and _is_status_field_name(item):
                return None
            if isinstance(item, Mapping):
                field = _string_from_paths(
                    (item,), ("field", "name", "key", "property", "attribute")
                )
                if field and _is_status_field_name(field):
                    extracted = _extract_status_from_value(item)
                    if extracted:
                        return extracted
        return None

    return None


def _extract_status_from_value(value: Any) -> str | None:
    if isinstance(value, str):
        return value.strip() or None

    if isinstance(value, Mapping):
        for path in (
            "newValue.name",
            "newValue",
            "new_value.name",
            "new_value",
            "after.name",
            "after",
            "to.name",
            "to",
            "value.name",
            "value",
            "name",
        ):
            extracted = _string_from_paths((value,), (path,))
            if extracted:
                return extracted

    return None


def _is_status_change_event(contexts: Iterable[Mapping[str, Any]]) -> bool:
    direct_event = False
    generic_issue_update = False

    for context in contexts:
        for key in EVENT_KEYS:
            value = context.get(key)
            if not isinstance(value, str):
                continue

            normalized = _normalize_text(value)
            compact = normalized.replace(" ", "")
            if compact in {"statuschanged", "statuschange", "statechanged", "statechange"}:
                direct_event = True
            if compact in {
                "issueupdated",
                "updatedissue",
                "update",
                "updated",
                "issueupdate",
            }:
                generic_issue_update = True

    return direct_event or (generic_issue_update and _has_status_change_details(contexts))


def _has_status_change_details(contexts: Iterable[Mapping[str, Any]]) -> bool:
    for context in contexts:
        for path in ("updatedFields", "changes", "changed", "change"):
            value = _value_at_path(context, path)
            if _mentions_status_field(value):
                return True
    return False


def _mentions_status_field(value: Any) -> bool:
    if isinstance(value, str):
        return _is_status_field_name(value)

    if isinstance(value, Mapping):
        return any(
            _is_status_field_name(str(key)) or _mentions_status_field(nested)
            for key, nested in value.items()
        )

    if isinstance(value, Iterable):
        return any(_mentions_status_field(item) for item in value)

    return False


def _is_status_field_name(value: str) -> bool:
    normalized = _normalize_text(value).replace(" ", "")
    return normalized in STATUS_FIELD_KEYS


def _has_prefix(title: str) -> bool:
    return title.lower().startswith(PREFIX.lower())


def _string_from_paths(
    contexts: Iterable[Mapping[str, Any]], paths: Iterable[str]
) -> str | None:
    for context in contexts:
        for path in paths:
            value = _value_at_path(context, path)
            if isinstance(value, str):
                stripped = value.strip()
                if stripped:
                    return stripped
            elif isinstance(value, (int, float)):
                return str(value)
    return None


def _value_at_path(context: Mapping[str, Any], path: str) -> Any:
    current: Any = context
    for part in path.split("."):
        if not isinstance(current, Mapping) or part not in current:
            return None
        current = current[part]
    return current


def _normalize_text(value: str | None) -> str:
    if not value:
        return ""
    with_spaces = re.sub(r"([a-z0-9])([A-Z])", r"\1 \2", value)
    with_spaces = re.sub(r"[_\-]+", " ", with_spaces)
    with_spaces = re.sub(r"[^A-Za-z0-9]+", " ", with_spaces)
    return re.sub(r"\s+", " ", with_spaces).strip().lower()


def main() -> int:
    try:
        event = json.load(sys.stdin)
    except json.JSONDecodeError as error:
        print(f"Invalid JSON: {error}", file=sys.stderr)
        return 1

    update = build_issue_title_update(event)
    if update is not None:
        print(json.dumps(update, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
