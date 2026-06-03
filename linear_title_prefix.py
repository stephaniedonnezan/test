"""Build Linear issue title update actions for research-status transitions."""

from __future__ import annotations

import json
import re
import sys
from collections.abc import Mapping
from typing import Any


TITLE_PREFIX = "Cursor researching"
RESEARCH_STATUS = "to research"
STATUS_FIELD_NAMES = {"status", "state", "workflowstate", "workflowstatus"}
STATUS_CHANGE_TOKENS = {
    "statuschanged",
    "statuschange",
    "statusupdated",
    "statechanged",
    "statechange",
    "workflowstatechanged",
}
UPDATE_TOKENS = {
    "update",
    "updated",
    "issueupdated",
    "updatedissue",
}


def build_issue_title_update(event: Mapping[str, Any] | None) -> dict[str, str] | None:
    """Return a Linear issue title update action when an issue enters research.

    The automation trigger payload is flat, but Linear webhooks are often nested
    under ``triggerContext`` or ``data.issue``. This function accepts both forms.
    """

    if not isinstance(event, Mapping):
        return None

    flattened = _flatten_payload(event)
    if not _is_status_change_event(flattened):
        return None

    new_status = _first_text(
        flattened,
        "newStatus",
        "new_status",
        "status",
        "state",
        "workflowState",
        "workflow_status",
    )
    if _normalize_text(new_status) != _normalize_text(RESEARCH_STATUS):
        return None

    issue_id = _first_text(flattened, "issueId", "issue_id", "identifier", "id")
    title = _first_text(flattened, "title")
    if not issue_id or not title:
        return None

    clean_title = title.strip()
    if not clean_title or _has_title_prefix(clean_title):
        return None

    return {
        "action": "update_issue_title",
        "issueId": issue_id.strip(),
        "title": f"{TITLE_PREFIX}: {clean_title}",
    }


def _flatten_payload(event: Mapping[str, Any]) -> dict[str, Any]:
    """Merge useful Linear payload layers, preferring explicit trigger fields."""

    layers: list[Mapping[str, Any]] = []

    trigger_context = event.get("triggerContext")
    data = event.get("data")
    issue = data.get("issue") if isinstance(data, Mapping) else event.get("issue")

    for layer in (issue, data, trigger_context, event):
        if isinstance(layer, Mapping):
            layers.append(layer)

    flattened: dict[str, Any] = {}
    for layer in layers:
        for key, value in layer.items():
            if isinstance(value, Mapping) and _normalize_text(key) in STATUS_FIELD_NAMES:
                name = value.get("name")
                if isinstance(name, str):
                    flattened[key] = name
                    continue
            flattened[key] = value

    if isinstance(issue, Mapping):
        issue_id = _first_text(issue, "id", "issueId", "issue_id", "identifier")
        if issue_id:
            flattened["issueId"] = issue_id
        issue_title = _first_text(issue, "title")
        if issue_title and not _first_text(flattened, "title"):
            flattened["title"] = issue_title

    return flattened


def _is_status_change_event(payload: Mapping[str, Any]) -> bool:
    trigger_values = [
        _normalize_text(value)
        for key in ("trigger", "webhookType", "action", "type")
        if (value := _text_value(payload.get(key)))
    ]

    if any(value in STATUS_CHANGE_TOKENS for value in trigger_values):
        return True

    if any(value in UPDATE_TOKENS for value in trigger_values):
        return _updated_status_fields(payload)

    return False


def _updated_status_fields(payload: Mapping[str, Any]) -> bool:
    updated_fields = (
        payload.get("updatedFields")
        or payload.get("updated_fields")
        or payload.get("changedFields")
        or payload.get("changed_fields")
    )
    if isinstance(updated_fields, str):
        fields = [updated_fields]
    elif isinstance(updated_fields, list | tuple | set):
        fields = [str(field) for field in updated_fields]
    else:
        fields = []

    return any(_normalize_text(field) in STATUS_FIELD_NAMES for field in fields)


def _first_text(payload: Mapping[str, Any], *keys: str) -> str | None:
    for key in keys:
        value = payload.get(key)
        text = _text_value(value)
        if text is not None:
            return text
    return None


def _text_value(value: Any) -> str | None:
    if isinstance(value, str):
        return value
    if isinstance(value, Mapping):
        name = value.get("name") or value.get("title")
        return name if isinstance(name, str) else None
    return None


def _has_title_prefix(title: str) -> bool:
    normalized_title = _normalize_text(title)
    normalized_prefix = _normalize_text(TITLE_PREFIX)
    return normalized_title == normalized_prefix or normalized_title.startswith(
        normalized_prefix
    )


def _normalize_text(value: str | None) -> str:
    if value is None:
        return ""

    value = re.sub(r"([a-z0-9])([A-Z])", r"\1 \2", value)
    return re.sub(r"[^a-z0-9]+", "", value.lower())


def main() -> int:
    event = json.load(sys.stdin)
    action = build_issue_title_update(event)
    if action is not None:
        json.dump(action, sys.stdout)
        sys.stdout.write("\n")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
