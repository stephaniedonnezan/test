"""Build Linear issue title update actions for research status changes."""

from __future__ import annotations

import json
import re
import sys
from collections.abc import Mapping
from typing import Any


TITLE_PREFIX = "Cursor researching"
RESEARCH_STATUS = "to research"
STATUS_FIELD_NAMES = {
    "status",
    "statusid",
    "status id",
    "state",
    "stateid",
    "state id",
    "workflowstate",
    "workflow state",
    "workflowstateid",
    "workflow state id",
    "workflow_status",
    "workflow status",
}


def build_issue_title_update(event: Mapping[str, Any]) -> dict[str, str] | None:
    """Return a Linear title update action when an issue moves to research."""
    if not isinstance(event, Mapping):
        return None

    candidates = _collect_candidates(event)
    if not _is_status_change_event(candidates):
        return None

    new_status = _extract_new_status(candidates)
    if _normalize_words(new_status) != RESEARCH_STATUS:
        return None

    issue_id = _extract_issue_id(candidates)
    title = _extract_title(candidates)
    if not issue_id or not title:
        return None

    if title.lower().startswith(TITLE_PREFIX.lower()):
        updated_title = title
    else:
        updated_title = f"{TITLE_PREFIX}: {title}"

    return {
        "action": "update_issue_title",
        "issueId": issue_id,
        "title": updated_title,
    }


def _collect_candidates(event: Mapping[str, Any]) -> list[Mapping[str, Any]]:
    candidates: list[Mapping[str, Any]] = []

    def add(value: Any) -> None:
        if isinstance(value, Mapping) and value not in candidates:
            candidates.append(value)

    add(event)
    add(event.get("triggerContext"))
    add(event.get("data"))
    data = event.get("data")
    if isinstance(data, Mapping):
        add(data.get("issue"))
        add(data.get("node"))
    add(event.get("issue"))
    add(event.get("node"))

    return candidates


def _is_status_change_event(candidates: list[Mapping[str, Any]]) -> bool:
    signals = _string_values_for_keys(
        candidates,
        ("trigger", "webhookType", "action", "type", "event", "eventType"),
    )
    if any(_is_direct_status_change_signal(signal) for signal in signals):
        return True

    is_update_event = any(_is_update_signal(signal) for signal in signals)
    return _has_status_change_metadata(candidates) and (
        is_update_event or not signals
    )


def _is_direct_status_change_signal(value: str) -> bool:
    compact = _normalize_words(value).replace(" ", "")
    return any(
        marker in compact
        for marker in (
            "statuschanged",
            "statuschange",
            "statechanged",
            "statechange",
            "workflowstatechanged",
            "workflowstatechange",
        )
    )


def _is_update_signal(value: str) -> bool:
    normalized = _normalize_words(value)
    compact = normalized.replace(" ", "")
    return normalized in {"update", "updated", "issue update", "issue updated"} or (
        "update" in compact
    )


def _has_status_change_metadata(candidates: list[Mapping[str, Any]]) -> bool:
    for candidate in candidates:
        for key in ("updatedFields", "changedFields"):
            if _field_collection_mentions_status(candidate.get(key)):
                return True

        if _mapping_keys_mention_status(candidate.get("changes")):
            return True

        if _mapping_keys_mention_status(candidate.get("updatedFrom")):
            return True

    return False


def _field_collection_mentions_status(value: Any) -> bool:
    if isinstance(value, str):
        return _is_status_field(value)

    if isinstance(value, Mapping):
        return any(
            _is_status_field(key) or _field_collection_mentions_status(nested)
            for key, nested in value.items()
        )

    if isinstance(value, list | tuple | set):
        for item in value:
            if _field_collection_mentions_status(item):
                return True
            if isinstance(item, Mapping):
                for key in ("field", "name", "key", "path"):
                    if _is_status_field(item.get(key)):
                        return True

    return False


def _mapping_keys_mention_status(value: Any) -> bool:
    if isinstance(value, Mapping):
        return any(_is_status_field(key) for key in value.keys())

    if isinstance(value, list | tuple | set):
        return any(_field_collection_mentions_status(item) for item in value)

    return False


def _extract_new_status(candidates: list[Mapping[str, Any]]) -> str | None:
    explicit_keys = (
        "newStatus",
        "new_status",
        "toStatus",
        "to_status",
        "statusName",
        "status_name",
        "stateName",
        "state_name",
        "workflowStateName",
        "workflow_state_name",
    )
    for key in explicit_keys:
        value = _first_value_for_key(candidates, key)
        status = _string_from_status_value(value)
        if status:
            return status

    for candidate in candidates:
        status = _new_status_from_changes(candidate.get("changes"))
        if status:
            return status

    fallback_keys = ("status", "state", "workflowState", "workflow_state")
    for key in fallback_keys:
        value = _first_value_for_key(candidates, key)
        status = _string_from_status_value(value)
        if status:
            return status

    return None


def _new_status_from_changes(value: Any) -> str | None:
    if isinstance(value, Mapping):
        for key, change in value.items():
            if not _is_status_field(key):
                continue
            status = _new_status_from_change_value(change)
            if status:
                return status

    if isinstance(value, list | tuple | set):
        for change in value:
            if not isinstance(change, Mapping):
                continue
            field = next(
                (change.get(key) for key in ("field", "name", "key", "path")),
                None,
            )
            if _is_status_field(field):
                status = _new_status_from_change_value(change)
                if status:
                    return status

    return None


def _new_status_from_change_value(value: Any) -> str | None:
    if isinstance(value, Mapping):
        for key in ("newValue", "new_value", "to", "after", "new", "value"):
            status = _string_from_status_value(value.get(key))
            if status:
                return status
        return _string_from_status_value(value)

    return _string_from_status_value(value)


def _extract_issue_id(candidates: list[Mapping[str, Any]]) -> str | None:
    for key in ("issueId", "issue_id", "identifier", "key"):
        value = _first_value_for_key(candidates, key)
        issue_id = _clean_string(value)
        if issue_id:
            return issue_id

    value = _first_value_for_key(candidates, "id")
    return _clean_string(value)


def _extract_title(candidates: list[Mapping[str, Any]]) -> str | None:
    value = _first_value_for_key(candidates, "title")
    return _clean_string(value)


def _first_value_for_key(candidates: list[Mapping[str, Any]], key: str) -> Any:
    for candidate in candidates:
        if key in candidate:
            return candidate[key]
    return None


def _string_values_for_keys(
    candidates: list[Mapping[str, Any]], keys: tuple[str, ...]
) -> list[str]:
    values: list[str] = []
    for candidate in candidates:
        for key in keys:
            value = _clean_string(candidate.get(key))
            if value:
                values.append(value)
    return values


def _string_from_status_value(value: Any) -> str | None:
    if isinstance(value, str):
        return _clean_string(value)

    if isinstance(value, Mapping):
        for key in ("name", "title", "displayName", "label"):
            status = _clean_string(value.get(key))
            if status:
                return status

    return None


def _is_status_field(value: Any) -> bool:
    normalized = _normalize_words(value)
    compact = normalized.replace(" ", "")
    return normalized in STATUS_FIELD_NAMES or compact in STATUS_FIELD_NAMES


def _normalize_words(value: Any) -> str:
    text = _clean_string(value)
    if not text:
        return ""
    text = re.sub(r"([a-z0-9])([A-Z])", r"\1 \2", text)
    text = re.sub(r"[^A-Za-z0-9]+", " ", text)
    return " ".join(text.lower().split())


def _clean_string(value: Any) -> str | None:
    if isinstance(value, str):
        stripped = value.strip()
        return stripped or None
    return None


def main() -> int:
    event = json.load(sys.stdin)
    update = build_issue_title_update(event)
    if update is not None:
        print(json.dumps(update, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
