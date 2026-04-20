"""Helpers for updating Linear issue titles from status webhooks."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any


RESEARCHING_PREFIX = "Cursor researching"
TARGET_STATUS = "to research"


@dataclass(frozen=True)
class TitleUpdateResult:
    """Represents the outcome of evaluating a webhook payload."""

    should_update: bool
    current_title: str
    new_title: str
    reason: str


def _normalize(value: Any) -> str:
    return str(value or "").strip().casefold()


def _is_already_prefixed(title: str) -> bool:
    return _normalize(title).startswith(_normalize(RESEARCHING_PREFIX))


def _prefix_title(title: str) -> str:
    return f"{RESEARCHING_PREFIX}: {title}".strip()


def evaluate_issue_title_update(payload: dict[str, Any]) -> TitleUpdateResult:
    """Return the title update decision for a Linear status-changed webhook."""

    trigger_context = payload.get("triggerContext", payload)
    new_status = _normalize(trigger_context.get("newStatus"))
    current_title = str(trigger_context.get("title") or "").strip()

    if not current_title:
        return TitleUpdateResult(
            should_update=False,
            current_title="",
            new_title="",
            reason="missing issue title",
        )

    if new_status != TARGET_STATUS:
        return TitleUpdateResult(
            should_update=False,
            current_title=current_title,
            new_title=current_title,
            reason=f"status is not {TARGET_STATUS!r}",
        )

    if _is_already_prefixed(current_title):
        return TitleUpdateResult(
            should_update=False,
            current_title=current_title,
            new_title=current_title,
            reason="title already prefixed",
        )

    return TitleUpdateResult(
        should_update=True,
        current_title=current_title,
        new_title=_prefix_title(current_title),
        reason="status moved to to research",
    )
