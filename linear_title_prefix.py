"""Helpers for adding the Cursor research prefix to Linear issue titles."""

from __future__ import annotations

import argparse
import json
import re
import sys
from collections.abc import Mapping
from typing import Any

RESEARCH_TITLE_PREFIX = "Cursor researching"
RESEARCH_STATUS_NAME = "to research"

_STATUS_CHANGED_MARKERS = {
    "status changed",
    "status change",
    "status updated",
}
_ISSUE_UPDATED_MARKERS = {
    "issue updated",
    "updated issue",
    "update",
    "updated",
}
_STATUS_FIELD_NAMES = {
    "status",
    "state",
    "stateid",
    "workflowstate",
    "workflowstateid",
}
_PREFIX_PATTERN = re.compile(
    rf"^\s*{re.escape(RESEARCH_TITLE_PREFIX)}(?:\s*[-:]\s*|\s+|$)",
    flags=re.IGNORECASE,
)


def update_issue_title_for_status(title: str, new_status: str) -> str:
    """Return the title prefixed when the new status is `to research`."""
    if _normalize_text(new_status) != RESEARCH_STATUS_NAME:
        return title

    return prefix_research_title(title)


def prefix_research_title(title: str) -> str:
    """Add the Cursor research prefix without duplicating existing prefixes."""
    if _PREFIX_PATTERN.match(title):
        return title

    clean_title = title.strip()
    if not clean_title:
        return RESEARCH_TITLE_PREFIX
    return f"{RESEARCH_TITLE_PREFIX} - {clean_title}"


def derive_updated_title(payload: Mapping[str, Any]) -> str | None:
    """Return an updated title for a supported Linear status-change payload."""
    merged_payload = _collect_payload(payload)
    if not _is_status_change_event(merged_payload):
        return None

    title = _first_text(merged_payload, ("title",))
    new_status = _new_status(merged_payload)
    if title is None or new_status is None:
        return None

    updated_title = update_issue_title_for_status(title=title, new_status=new_status)
    if updated_title == title:
        return None
    return updated_title


def build_issue_title_update(payload: Mapping[str, Any]) -> dict[str, str] | None:
    """Build an issue-title update action for automations that need metadata."""
    merged_payload = _collect_payload(payload)
    updated_title = derive_updated_title(merged_payload)
    if updated_title is None:
        return None

    issue_id = _first_text(merged_payload, ("id", "issueId", "issue_id", "identifier"))
    if issue_id is None:
        return {"action": "update_issue_title", "title": updated_title}

    return {
        "action": "update_issue_title",
        "issueId": issue_id.strip(),
        "title": updated_title,
    }


def _collect_payload(payload: Mapping[str, Any]) -> dict[str, Any]:
    """Flatten common automation and Linear webhook wrappers into one payload."""
    merged: dict[str, Any] = {}

    def merge(value: Any) -> None:
        if not isinstance(value, Mapping):
            return
        for nested_key in ("triggerContext", "issue", "data"):
            nested_value = value.get(nested_key)
            if isinstance(nested_value, Mapping):
                merge(nested_value)
        merged.update(value)

    merge(payload)
    return merged


def _is_status_change_event(payload: Mapping[str, Any]) -> bool:
    event_markers = {
        normalized
        for key in ("trigger", "webhookType", "action", "type")
        if (normalized := _normalize_text(payload.get(key))) is not None
    }

    if event_markers & _STATUS_CHANGED_MARKERS:
        return True

    if event_markers & _ISSUE_UPDATED_MARKERS:
        return _has_changed_status_field(payload)

    return False


def _has_changed_status_field(payload: Mapping[str, Any]) -> bool:
    changed_fields = payload.get("updatedFields") or payload.get("changedFields")
    if _field_list_mentions_status(changed_fields):
        return True

    updated_from = payload.get("updatedFrom") or payload.get("previousValues")
    if isinstance(updated_from, Mapping):
        return any(_normalize_key(key) in _STATUS_FIELD_NAMES for key in updated_from)

    return False


def _field_list_mentions_status(value: Any) -> bool:
    if isinstance(value, str):
        values: list[Any] = [value]
    elif isinstance(value, (list, tuple, set)):
        values = list(value)
    else:
        return False

    return any(_normalize_key(field) in _STATUS_FIELD_NAMES for field in values)


def _new_status(payload: Mapping[str, Any]) -> str | None:
    explicit_status = _first_text(
        payload,
        (
            "newStatus",
            "new_status",
            "statusName",
            "stateName",
            "workflowStateName",
        ),
    )
    if explicit_status is not None:
        return explicit_status

    for key in ("status", "state", "workflowState"):
        value = payload.get(key)
        if isinstance(value, Mapping):
            name = _first_text(value, ("name", "title"))
            if name is not None:
                return name
        elif isinstance(value, str):
            return value

    return None


def _first_text(payload: Mapping[str, Any], keys: tuple[str, ...]) -> str | None:
    for key in keys:
        value = payload.get(key)
        if isinstance(value, str) and value.strip():
            return value
        if isinstance(value, (int, float)):
            return str(value)
    return None


def _normalize_text(value: Any) -> str | None:
    if not isinstance(value, str):
        return None

    words = _split_words(value)
    if not words:
        return None
    return " ".join(words)


def _normalize_key(value: Any) -> str | None:
    if not isinstance(value, str):
        return None

    words = _split_words(value)
    if not words:
        return None
    return "".join(words)


def _split_words(value: str) -> list[str]:
    spaced = re.sub(r"([a-z0-9])([A-Z])", r"\1 \2", value.strip())
    return re.findall(r"[a-z0-9]+", spaced.lower())


def _load_payload(input_path: str | None) -> Mapping[str, Any]:
    if input_path:
        with open(input_path, encoding="utf-8") as input_file:
            payload = json.load(input_file)
    else:
        payload = json.load(sys.stdin)

    if not isinstance(payload, Mapping):
        raise ValueError("Input payload must be a JSON object.")
    return payload


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="Prefix Linear issue titles when status changes to to research."
    )
    parser.add_argument(
        "--input",
        help="Path to input JSON payload (reads from stdin if omitted).",
    )
    parser.add_argument(
        "--action",
        action="store_true",
        help="Emit an update action object instead of only the updated title.",
    )
    args = parser.parse_args(argv)

    payload = _load_payload(args.input)
    if args.action:
        output: dict[str, str | None] | None = build_issue_title_update(payload)
    else:
        output = {"updatedTitle": derive_updated_title(payload)}

    print(json.dumps(output))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
