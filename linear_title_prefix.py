"""Build title update actions for Linear issues entering research."""

from collections.abc import Mapping
import re
from typing import Any


TITLE_PREFIX = "Cursor researching"
TARGET_STATUS = "to research"
STATUS_FIELDS = ("newStatus", "new_status", "status")
ISSUE_ID_FIELDS = ("id", "issueId", "issue_id", "identifier")
TITLE_FIELDS = ("title", "name")
TRIGGER_FIELDS = ("trigger", "action", "type", "webhookType")
STATUS_CHANGE_TOKENS = {
    "statuschanged",
    "statuschange",
    "statusupdate",
    "statechanged",
    "statechange",
}
ISSUE_UPDATED_TOKENS = {"issueupdated", "updatedissue"}


def build_issue_title_update(event: Any) -> dict[str, str] | None:
    """Return an issue-title update action when a Linear issue moves to research.

    The Cursor automation payload may be flat or nested under ``triggerContext``,
    ``data.issue``, or ``issue``. This function only describes the update to
    perform; the automation runner is responsible for applying it to Linear.
    """

    if not isinstance(event, Mapping):
        return None

    contexts = _contexts(event)
    if not _is_status_change(contexts):
        return None

    if _normalize_status(_status(contexts)) != TARGET_STATUS:
        return None

    issue_id = _string_field(contexts, ISSUE_ID_FIELDS)
    title = _string_field(contexts, TITLE_FIELDS)
    if not issue_id or not title:
        return None

    if _has_title_prefix(title):
        return None

    return {
        "action": "update_issue_title",
        "issueId": issue_id,
        "title": f"{TITLE_PREFIX}: {title}",
    }


def _contexts(event: Mapping[str, Any]) -> list[Mapping[str, Any]]:
    contexts: list[Mapping[str, Any]] = []

    def add(value: Any) -> None:
        if isinstance(value, Mapping) and value not in contexts:
            contexts.append(value)

    add(event)
    add(event.get("triggerContext"))
    add(event.get("data"))
    data = event.get("data")
    if isinstance(data, Mapping):
        add(data.get("issue"))
    add(event.get("issue"))
    trigger_context = event.get("triggerContext")
    if isinstance(trigger_context, Mapping):
        add(trigger_context.get("issue"))

    return contexts


def _is_status_change(contexts: list[Mapping[str, Any]]) -> bool:
    for field in TRIGGER_FIELDS:
        raw_value = _field(contexts, (field,))
        token = _normalize_token(raw_value)
        if token in STATUS_CHANGE_TOKENS:
            return True

        if token in ISSUE_UPDATED_TOKENS:
            return _updated_fields_include_status(contexts)

    return False


def _updated_fields_include_status(contexts: list[Mapping[str, Any]]) -> bool:
    raw_value = _field(contexts, ("updatedFields", "updated_fields", "changes"))
    if raw_value is None:
        return False

    if isinstance(raw_value, Mapping):
        values = raw_value.keys()
    elif isinstance(raw_value, str):
        values = re.split(r"[,;\s]+", raw_value)
    else:
        try:
            values = list(raw_value)
        except TypeError:
            return False

    return any(_normalize_token(value) in {"status", "state"} for value in values)


def _status(contexts: list[Mapping[str, Any]]) -> Any:
    value = _field(contexts, STATUS_FIELDS)
    if value is not None:
        return value

    state = _field(contexts, ("state",))
    if isinstance(state, Mapping):
        return state.get("name")

    return None


def _field(contexts: list[Mapping[str, Any]], names: tuple[str, ...]) -> Any:
    for context in contexts:
        for name in names:
            if name in context:
                return context[name]
    return None


def _string_field(contexts: list[Mapping[str, Any]], names: tuple[str, ...]) -> str | None:
    value = _field(contexts, names)
    if value is None:
        return None

    text = str(value).strip()
    return text or None


def _has_title_prefix(title: str) -> bool:
    return title.casefold().startswith(TITLE_PREFIX.casefold())


def _normalize_status(value: Any) -> str | None:
    if value is None:
        return None

    normalized = _split_camel_case(str(value))
    normalized = re.sub(r"[_\-]+", " ", normalized)
    normalized = re.sub(r"\s+", " ", normalized).strip().casefold()
    return normalized or None


def _normalize_token(value: Any) -> str | None:
    normalized = _normalize_status(value)
    if normalized is None:
        return None
    return normalized.replace(" ", "")


def _split_camel_case(value: str) -> str:
    value = re.sub(r"([a-z0-9])([A-Z])", r"\1 \2", value)
    return re.sub(r"([A-Z]+)([A-Z][a-z])", r"\1 \2", value)
