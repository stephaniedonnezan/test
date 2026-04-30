"""Build Linear issue title updates for research status changes."""

from collections.abc import Mapping
import re
from typing import Any


PREFIX = "Cursor researching"
PREFIXED_TITLE_FORMAT = f"{PREFIX}: {{title}}"


def build_issue_title_update(event: Mapping[str, Any] | None) -> dict[str, str] | None:
    """Return a Linear issue title update when an issue moves to research.

    The automation trigger can pass Linear metadata at the top level, under
    ``triggerContext``, or within ``data`` / ``issue``. This function accepts
    those common shapes and returns a serializable action for the caller to
    apply.
    """

    if not isinstance(event, Mapping):
        return None

    payload = _flatten_event(event)

    if not _is_status_changed(payload):
        return None

    if _normalize_value(_first_value(payload, "newStatus", "new_status", "status", "state.name")) != "to research":
        return None

    issue_id = _string_value(_first_value(payload, "id", "issueId", "issue_id", "identifier"))
    title = _string_value(_first_value(payload, "title", "name"))

    if issue_id is None or title is None:
        return None

    title = title.strip()
    if not title or title.lower().startswith(PREFIX.lower()):
        return None

    return {
        "action": "update_issue_title",
        "issueId": issue_id,
        "title": PREFIXED_TITLE_FORMAT.format(title=title),
    }


def _flatten_event(event: Mapping[str, Any]) -> dict[str, Any]:
    """Merge common Linear wrapper objects into one lookup dictionary."""

    flattened: dict[str, Any] = {}

    def merge(value: Any) -> None:
        if isinstance(value, Mapping):
            flattened.update(value)

    merge(event)
    trigger_context = event.get("triggerContext")
    data = event.get("data")
    issue = event.get("issue")

    merge(trigger_context)
    merge(data)
    if isinstance(data, Mapping):
        merge(data.get("issue"))
    if isinstance(trigger_context, Mapping):
        merge(trigger_context.get("issue"))
        merge(trigger_context.get("data"))
    merge(issue)

    return flattened


def _is_status_changed(payload: Mapping[str, Any]) -> bool:
    trigger = _first_value(payload, "trigger", "webhookType", "action", "type")
    return _normalize_value(trigger) == "status changed"


def _first_value(payload: Mapping[str, Any], *keys: str) -> Any:
    for key in keys:
        value = _nested_value(payload, key)
        if value is not None:
            return value
    return None


def _nested_value(payload: Mapping[str, Any], key: str) -> Any:
    current: Any = payload
    for part in key.split("."):
        if not isinstance(current, Mapping) or part not in current:
            return None
        current = current[part]
    return current


def _string_value(value: Any) -> str | None:
    if isinstance(value, str):
        return value
    return None


def _normalize_value(value: Any) -> str | None:
    if not isinstance(value, str):
        return None
    spaced = re.sub(r"(?<=[a-z0-9])(?=[A-Z])", " ", value)
    return re.sub(r"[\s_-]+", " ", spaced).strip().lower()
