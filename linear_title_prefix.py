"""Helpers for preparing Linear issue title updates from webhook payloads."""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from typing import Any


RESEARCH_STATUS = "to research"
RESEARCH_TITLE_PREFIX = "Cursor researching"


def build_issue_title_update(event: Mapping[str, Any] | None) -> dict[str, str] | None:
    """Return a title-update action when a Linear issue moves to research.

    The automation payload can arrive either as the flattened Cursor automation
    trigger context or as a more direct Linear webhook payload. This function is
    deliberately side-effect free so the caller can decide how to apply the
    returned update to Linear.
    """

    if not isinstance(event, Mapping):
        return None

    if not _is_status_change_event(event):
        return None

    if _normalize_status(_extract_new_status(event)) != RESEARCH_STATUS:
        return None

    issue_id = _extract_issue_id(event)
    title = _extract_title(event)
    if not issue_id or not title:
        return None

    if _has_research_prefix(title):
        return None

    return {
        "action": "update_issue_title",
        "issueId": issue_id,
        "title": f"{RESEARCH_TITLE_PREFIX}: {title}",
    }


def handle_issue_status_changed(event: Mapping[str, Any] | None) -> dict[str, str] | None:
    """Compatibility wrapper used by status-change automation entry points."""

    return build_issue_title_update(event)


def _extract_new_status(event: Mapping[str, Any]) -> str | None:
    for payload in _candidate_payloads(event):
        value = _first_string(payload, ("newStatus", "new_status", "status"))
        if value:
            return value

        state_name = _nested_string(payload, ("state",), ("name",))
        if state_name:
            return state_name

        workflow_state_name = _nested_string(
            payload,
            ("workflowState", "workflow_state"),
            ("name",),
        )
        if workflow_state_name:
            return workflow_state_name

    return None


def _extract_issue_id(event: Mapping[str, Any]) -> str | None:
    for payload in _candidate_payloads(event):
        value = _first_string(payload, ("issueId", "issue_id", "id", "identifier"))
        if value:
            return value.strip()

    return None


def _extract_title(event: Mapping[str, Any]) -> str | None:
    for payload in _candidate_payloads(event):
        value = _first_string(payload, ("title", "name"))
        if value:
            return value.strip()

    return None


def _candidate_payloads(event: Mapping[str, Any]) -> list[Mapping[str, Any]]:
    candidates: list[Mapping[str, Any]] = [event]

    for key in ("triggerContext", "data", "issue"):
        nested = event.get(key)
        if isinstance(nested, Mapping):
            candidates.append(nested)

    data = event.get("data")
    if isinstance(data, Mapping):
        issue = data.get("issue")
        if isinstance(issue, Mapping):
            candidates.append(issue)

    trigger_context = event.get("triggerContext")
    if isinstance(trigger_context, Mapping):
        for key in ("data", "issue"):
            nested = trigger_context.get(key)
            if isinstance(nested, Mapping):
                candidates.append(nested)
        data = trigger_context.get("data")
        if isinstance(data, Mapping):
            issue = data.get("issue")
            if isinstance(issue, Mapping):
                candidates.append(issue)

    return candidates


def _is_status_change_event(event: Mapping[str, Any]) -> bool:
    for payload in _candidate_payloads(event):
        trigger = _normalize_token(_first_string(payload, ("trigger", "triggerType")))
        webhook_type = _normalize_token(_first_string(payload, ("webhookType", "type")))
        action = _normalize_token(_first_string(payload, ("action",)))

        if trigger in {"statuschanged", "statechanged", "workflowstatechanged"}:
            return True

        if action in {"statuschanged", "statechanged", "workflowstatechanged"}:
            return True

        if webhook_type in {"issueupdated", "updatedissue"}:
            if _updated_fields_include_status(payload):
                return True

        if webhook_type == "issue" and action in {"update", "updated", "issueupdated"}:
            if _updated_fields_include_status(payload):
                return True

        if webhook_type == "issue" and _has_any_status(payload):
            return True

    return False


def _has_any_status(payload: Mapping[str, Any]) -> bool:
    return bool(
        _first_string(payload, ("newStatus", "new_status", "status"))
        or _nested_string(payload, ("state",), ("name",))
        or _nested_string(payload, ("workflowState", "workflow_state"), ("name",))
    )


def _updated_fields_include_status(payload: Mapping[str, Any]) -> bool:
    updated_fields = payload.get("updatedFields")
    if updated_fields is None:
        updated_fields = payload.get("updated_fields")

    if isinstance(updated_fields, str):
        return _normalize_token(updated_fields) in {"status", "state", "workflowstate"}

    if isinstance(updated_fields, Sequence) and not isinstance(
        updated_fields, (str, bytes, bytearray)
    ):
        return any(
            _normalize_token(field) in {"status", "state", "workflowstate"}
            for field in updated_fields
        )

    return False


def _first_string(payload: Mapping[str, Any], keys: tuple[str, ...]) -> str | None:
    for key in keys:
        value = payload.get(key)
        if isinstance(value, str) and value.strip():
            return value
    return None


def _nested_string(
    payload: Mapping[str, Any],
    parent_keys: tuple[str, ...],
    child_keys: tuple[str, ...],
) -> str | None:
    for parent_key in parent_keys:
        nested = payload.get(parent_key)
        if isinstance(nested, Mapping):
            value = _first_string(nested, child_keys)
            if value:
                return value
    return None


def _normalize_status(value: str | None) -> str | None:
    if value is None:
        return None
    return " ".join(value.strip().casefold().replace("_", " ").replace("-", " ").split())


def _normalize_token(value: Any) -> str | None:
    if not isinstance(value, str):
        return None
    return "".join(character for character in value.casefold() if character.isalnum())


def _has_research_prefix(title: str) -> bool:
    return title.strip().casefold().startswith(RESEARCH_TITLE_PREFIX.casefold())
