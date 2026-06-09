"""Build Linear issue title updates for Cursor research status changes.

The automation receives either Cursor's flattened trigger context or Linear's
native webhook payload.  This module intentionally returns a small structured
action instead of calling Linear directly, so it is easy for the caller to test
and decide how to perform the mutation.
"""

from __future__ import annotations

import json
import re
import sys
from typing import Any


RESEARCH_STATUS = "to research"
TITLE_PREFIX = "Cursor researching"


def build_issue_title_update(event: dict[str, Any]) -> dict[str, str] | None:
    """Return a title-update action when an issue moves to "to research".

    The returned action has this shape:
    {
        "action": "update_issue_title",
        "issueId": "...",
        "title": "Cursor researching: original title"
    }

    None means the payload is not a relevant status change, has insufficient
    issue data, or already contains the requested prefix.
    """

    issue = _extract_issue(event)
    issue_id = _coerce_text(
        issue.get("id")
        or issue.get("identifier")
        or event.get("id")
        or event.get("issueId")
        or event.get("identifier")
    )
    title = _coerce_text(issue.get("title") or event.get("title"))

    if not issue_id or not title:
        return None

    if not _is_status_change(event):
        return None

    if _normalize_status(_extract_new_status(event, issue)) != RESEARCH_STATUS:
        return None

    if _has_research_prefix(title):
        return None

    return {
        "action": "update_issue_title",
        "issueId": issue_id,
        "title": f"{TITLE_PREFIX}: {title}",
    }


def _extract_issue(event: dict[str, Any]) -> dict[str, Any]:
    """Find issue details across Cursor and Linear webhook shapes."""

    data = event.get("data")
    if isinstance(data, dict):
        issue = data.get("issue")
        if isinstance(issue, dict):
            return issue

        # Some Linear payloads place the issue fields directly under data.
        if data.get("title") or data.get("identifier") or data.get("id"):
            return data

    issue = event.get("issue")
    if isinstance(issue, dict):
        return issue

    return event


def _is_status_change(event: dict[str, Any]) -> bool:
    """Detect status/state changes without requiring one exact webhook schema."""

    if "trigger" in event:
        trigger = _coerce_text(event.get("trigger")).lower()
        return trigger in {"status_changed", "state_changed"}

    event_type = _coerce_text(event.get("type")).lower()
    if event_type in {"status_changed", "state_changed"}:
        return True

    updated_fields = event.get("updatedFields")
    data = event.get("data")
    if isinstance(data, dict):
        updated_fields = updated_fields or data.get("updatedFields")

    if isinstance(updated_fields, list):
        status_fields = {"status", "statusid", "state", "stateid"}
        normalized_fields = {
            re.sub(r"[\W_]+", "", _coerce_text(field)).lower()
            for field in updated_fields
        }
        if normalized_fields & status_fields:
            return True

    # Cursor's flattened event includes newStatus for this trigger. Only use it
    # as a fallback when no explicit non-status trigger was supplied.
    return event.get("newStatus") is not None


def _extract_new_status(event: dict[str, Any], issue: dict[str, Any]) -> Any:
    """Read the destination status from common Cursor and Linear locations."""

    for key in ("newStatus", "status", "state"):
        if key in event:
            return event[key]

    data = event.get("data")
    if isinstance(data, dict):
        for key in ("newStatus", "status", "state"):
            if key in data:
                return data[key]

    for key in ("status", "state"):
        if key in issue:
            return issue[key]

    return None


def _normalize_status(value: Any) -> str:
    text = _coerce_text(value)
    text = re.sub(r"[-_]+", " ", text)
    text = re.sub(r"\s+", " ", text)
    return text.strip().lower()


def _coerce_text(value: Any) -> str:
    if value is None:
        return ""

    if isinstance(value, dict):
        for key in ("name", "title", "label", "status"):
            if key in value:
                return _coerce_text(value[key])
        return ""

    return str(value).strip()


def _has_research_prefix(title: str) -> bool:
    return re.match(rf"^\s*{re.escape(TITLE_PREFIX)}\b", title, re.IGNORECASE) is not None


def main() -> int:
    event = json.load(sys.stdin)
    action = build_issue_title_update(event)
    if action is None:
        return 0

    json.dump(action, sys.stdout, indent=2, sort_keys=True)
    sys.stdout.write("\n")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
