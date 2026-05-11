"""Build Linear issue title updates for issues entering research."""

from __future__ import annotations

import argparse
import json
import re
import sys
from collections.abc import Mapping
from typing import Any

RESEARCH_TITLE_PREFIX = "Cursor researching"
RESEARCH_STATUS_NAME = "to research"
UPDATE_ISSUE_TITLE_ACTION = "update_issue_title"

# Backwards-compatible aliases used by earlier automations.
TITLE_PREFIX = RESEARCH_TITLE_PREFIX
TARGET_STATUS = RESEARCH_STATUS_NAME

_STATUS_CHANGE_TOKENS = {
    "statuschanged",
    "statuschange",
    "statusupdated",
    "statechanged",
    "workflowstatechanged",
}
_ISSUE_UPDATED_TOKENS = {"issueupdated", "updatedissue", "updateissue"}
_STATUS_FIELD_TOKENS = {"status", "state", "workflowstate", "stateid", "statusid"}
_PREFIX_PATTERN = re.compile(
    rf"^\s*{re.escape(RESEARCH_TITLE_PREFIX)}(?:\b|$)", flags=re.IGNORECASE
)


def build_issue_title_update(event: Mapping[str, Any] | None) -> dict[str, str] | None:
    """Return a Linear title update when an issue moves to ``to research``.

    The helper accepts the flattened automation payload shape used by Cursor
    automations and common nested Linear webhook shapes under ``triggerContext``,
    ``data``, and ``issue``.
    """

    if not isinstance(event, Mapping):
        return None

    payload = _flatten_payload(event)
    if not _is_status_change(payload):
        return None

    new_status = _first_text(
        payload,
        ("newStatus", "new_status", "status", "statusName"),
        nested=(("state", "name"), ("workflowState", "name")),
    )
    if _normalize_status(new_status) != RESEARCH_STATUS_NAME:
        return None

    issue_id = _first_text(payload, ("issueId", "issue_id", "id", "identifier"))
    title = _first_text(payload, ("title", "name"))
    if not issue_id or not title:
        return None

    prefixed_title = prefix_issue_title(title)
    if prefixed_title == title.strip():
        return None

    return {
        "action": UPDATE_ISSUE_TITLE_ACTION,
        "issueId": issue_id.strip(),
        "title": prefixed_title,
    }


def handle_issue_status_changed(event: Mapping[str, Any] | None) -> dict[str, str] | None:
    """Compatibility wrapper for older automation entrypoints."""

    return build_issue_title_update(event)


def prefix_issue_title(title: str, prefix: str = RESEARCH_TITLE_PREFIX) -> str:
    """Prefix a title with ``Cursor researching`` while avoiding duplicates."""

    stripped_title = title.strip()
    if _has_prefix(stripped_title, prefix):
        return stripped_title
    if not stripped_title:
        return prefix
    return f"{prefix}: {stripped_title}"


def update_issue_title_for_status(title: str, new_status: str) -> str:
    """Return the prefixed title when ``new_status`` is ``to research``."""

    if _normalize_status(new_status) != RESEARCH_STATUS_NAME:
        return title
    return prefix_issue_title(title)


def derive_updated_title(payload: Mapping[str, Any]) -> str | None:
    """Derive just the updated title from an automation payload, if needed."""

    update = build_issue_title_update(payload)
    if update is not None:
        return update["title"]

    if not isinstance(payload, Mapping):
        return None

    flattened = _flatten_payload(payload)
    if not _is_status_change(flattened):
        return None

    title = _first_text(flattened, ("title", "name"))
    new_status = _first_text(
        flattened,
        ("newStatus", "new_status", "status", "statusName"),
        nested=(("state", "name"), ("workflowState", "name")),
    )
    if not title or _normalize_status(new_status) != RESEARCH_STATUS_NAME:
        return None

    updated_title = prefix_issue_title(title)
    if updated_title == title.strip():
        return None
    return updated_title


def _flatten_payload(event: Mapping[str, Any]) -> dict[str, Any]:
    payload: dict[str, Any] = {}

    for key in ("triggerContext", "data", "issue"):
        value = event.get(key)
        if isinstance(value, Mapping):
            payload.update(_flatten_payload(value))

    # Preserve nested state lookups while allowing outer automation metadata
    # such as trigger/newStatus to override nested issue data.
    payload.update(event)
    return payload


def _is_status_change(payload: Mapping[str, Any]) -> bool:
    trigger_tokens = [
        token
        for token in (
            _normalize_token(payload.get("trigger")),
            _normalize_token(payload.get("action")),
            _normalize_token(payload.get("type")),
            _normalize_token(payload.get("webhookType")),
        )
        if token is not None
    ]

    if any(token in _STATUS_CHANGE_TOKENS for token in trigger_tokens):
        return True

    if any(token in _ISSUE_UPDATED_TOKENS for token in trigger_tokens):
        return _contains_status_field(
            payload.get("updatedFields")
            or payload.get("updated_fields")
            or payload.get("changedFields")
            or payload.get("changed_fields")
        )

    return False


def _contains_status_field(value: Any) -> bool:
    if isinstance(value, str):
        return _normalize_token(value) in _STATUS_FIELD_TOKENS

    if isinstance(value, Mapping):
        return any(_contains_status_field(key) for key in value.keys())

    if isinstance(value, (list, tuple, set, frozenset)):
        return any(_contains_status_field(item) for item in value)

    return False


def _first_text(
    payload: Mapping[str, Any],
    keys: tuple[str, ...],
    *,
    nested: tuple[tuple[str, str], ...] = (),
) -> str | None:
    for key in keys:
        value = payload.get(key)
        if isinstance(value, str):
            stripped = value.strip()
            if stripped:
                return stripped

    for parent_key, child_key in nested:
        parent = payload.get(parent_key)
        if isinstance(parent, Mapping):
            value = parent.get(child_key)
            if isinstance(value, str):
                stripped = value.strip()
                if stripped:
                    return stripped

    return None


def _has_prefix(title: str, prefix: str = RESEARCH_TITLE_PREFIX) -> bool:
    if prefix == RESEARCH_TITLE_PREFIX:
        return _PREFIX_PATTERN.match(title) is not None
    return re.match(rf"^\s*{re.escape(prefix)}(?:\b|$)", title, re.IGNORECASE) is not None


def _normalize_status(value: Any) -> str | None:
    if not isinstance(value, str):
        return None

    spaced = re.sub(r"(?<=[a-z0-9])(?=[A-Z])", " ", value)
    words = re.sub(r"[^a-zA-Z0-9]+", " ", spaced).strip().lower()
    return re.sub(r"\s+", " ", words)


def _normalize_token(value: Any) -> str | None:
    normalized = _normalize_status(value)
    if normalized is None:
        return None
    return normalized.replace(" ", "")


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
        description="Prefix a Linear issue title when its status changes to to research."
    )
    parser.add_argument(
        "--input",
        help="Path to an input JSON payload. Reads from stdin when omitted.",
    )
    args = parser.parse_args(argv)

    payload = _load_payload(args.input)
    print(json.dumps({"updatedTitle": derive_updated_title(payload)}))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
