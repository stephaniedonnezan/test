"""Build Linear issue-title updates for research status transitions."""

from collections.abc import Mapping
import re
from typing import Any


RESEARCH_STATUS = "to research"
TITLE_PREFIX = "Cursor researching"


def build_issue_title_update(event: Mapping[str, Any]) -> dict[str, str] | None:
    """Return a title update action when a Linear issue moves to research.

    The automation payloads used by Cursor and Linear have varied slightly over
    time, so this helper accepts both flat trigger payloads and nested Linear
    webhook-style objects.
    """

    if not isinstance(event, Mapping):
        return None

    payload = _flatten_payload(event)
    if not _is_status_change(payload):
        return None

    if _normalize_status(_first_present(payload, ("newStatus", "new_status", "status", "state"))) != RESEARCH_STATUS:
        return None

    issue_id = _first_present(payload, ("issueId", "issue_id", "id", "identifier"))
    title = _first_present(payload, ("title", "name"))
    if not issue_id or not isinstance(title, str):
        return None

    stripped_title = title.strip()
    if not stripped_title or _has_prefix(stripped_title):
        return None

    return {
        "action": "update_issue_title",
        "issueId": str(issue_id),
        "title": f"{TITLE_PREFIX}: {stripped_title}",
    }


def _flatten_payload(event: Mapping[str, Any]) -> dict[str, Any]:
    payload: dict[str, Any] = {}

    for candidate in _payload_candidates(event):
        payload.update(_extract_issue_fields(candidate))
        payload.update(candidate)

    return payload


def _payload_candidates(event: Mapping[str, Any]) -> list[Mapping[str, Any]]:
    candidates: list[Mapping[str, Any]] = []

    def add(value: Any) -> None:
        if isinstance(value, Mapping):
            candidates.append(value)

    trigger_context = event.get("triggerContext")
    data = event.get("data")

    if isinstance(trigger_context, Mapping):
        trigger_data = trigger_context.get("data")
        if isinstance(trigger_data, Mapping):
            add(trigger_data.get("issue"))
        add(trigger_context.get("data"))

    if isinstance(data, Mapping):
        add(data.get("issue"))
    add(data)
    add(trigger_context)
    add(event)

    return candidates


def _extract_issue_fields(candidate: Mapping[str, Any]) -> dict[str, Any]:
    issue = candidate.get("issue")
    if not isinstance(issue, Mapping):
        return {}

    fields = dict(issue)
    state = fields.get("state")
    if isinstance(state, Mapping):
        fields.setdefault("state", state.get("name"))
        fields.setdefault("status", state.get("name"))

    return fields


def _is_status_change(payload: Mapping[str, Any]) -> bool:
    trigger = _first_present(payload, ("trigger", "action", "type", "webhookType", "webhook_type"))
    if trigger is None:
        return True

    normalized_trigger = _normalize_status(trigger)
    return normalized_trigger in {
        "status changed",
        "status change",
        "statuschanged",
        "state changed",
        "state change",
        "issue updated",
        "issue update",
        "update",
    }


def _first_present(payload: Mapping[str, Any], keys: tuple[str, ...]) -> Any:
    for key in keys:
        value = payload.get(key)
        if value is not None:
            return value
    return None


def _normalize_status(value: Any) -> str:
    if isinstance(value, Mapping):
        value = value.get("name")
    if value is None:
        return ""

    text = str(value).strip()
    text = re.sub(r"(?<=[a-z0-9])(?=[A-Z])", " ", text)
    text = re.sub(r"[^A-Za-z0-9]+", " ", text)
    return " ".join(text.casefold().split())


def _has_prefix(title: str) -> bool:
    return title.casefold().startswith(TITLE_PREFIX.casefold())
