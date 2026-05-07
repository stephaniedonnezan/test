"""Build title updates for Linear issues entering the research status."""

from collections.abc import Mapping
import re


PREFIX = "Cursor researching"
TARGET_STATUS = "to research"


def build_issue_title_update(event):
    """Return a Linear title update action when an issue moves to research.

    The Cursor automation payload used by these tasks places issue metadata in
    ``triggerContext``, while Linear webhooks often nest it under ``data.issue``
    or ``issue``. This handler accepts those common shapes and returns ``None``
    for events that do not represent a status change to "to research".
    """
    if not isinstance(event, Mapping):
        return None

    contexts = _collect_contexts(event)
    if not _is_status_change(contexts):
        return None

    new_status = _first_value(contexts, ("newStatus", "new_status", "status"))
    if new_status is None:
        new_status = _nested_first_value(contexts, (("state", "name"), ("state", "title")))

    if _normalize_words(new_status) != TARGET_STATUS:
        return None

    issue_id = _string_value(
        _first_value(contexts, ("id", "issueId", "issue_id", "identifier"))
    )
    title = _string_value(_first_value(contexts, ("title", "name")))
    if not issue_id or not title:
        return None

    if title.lower().startswith(PREFIX.lower()):
        return None

    return {
        "action": "update_issue_title",
        "issueId": issue_id,
        "title": f"{PREFIX}: {title}",
    }


def _collect_contexts(event):
    """Return payload mappings from most-specific to least-specific."""
    contexts = []

    trigger_context = event.get("triggerContext")
    if isinstance(trigger_context, Mapping):
        contexts.append(trigger_context)

    data = event.get("data")
    if isinstance(data, Mapping):
        issue = data.get("issue")
        if isinstance(issue, Mapping):
            contexts.append(issue)
        contexts.append(data)

    issue = event.get("issue")
    if isinstance(issue, Mapping):
        contexts.append(issue)

    contexts.append(event)
    return contexts


def _is_status_change(contexts):
    trigger_values = (
        "trigger",
        "action",
        "type",
        "event",
        "webhookType",
        "webhook_type",
    )

    normalized_triggers = {
        _normalize_token(value)
        for value in (_first_value(contexts, trigger_values),)
        if value is not None
    }
    normalized_triggers.update(
        _normalize_token(context[key])
        for context in contexts
        for key in trigger_values
        if isinstance(context, Mapping) and key in context
    )

    if any(
        value in {"statuschanged", "statuschange", "statusupdated"}
        for value in normalized_triggers
    ):
        return True

    if any(value in {"issueupdated", "updated", "update"} for value in normalized_triggers):
        updated_fields = _first_value(contexts, ("updatedFields", "updated_fields"))
        return _contains_status_field(updated_fields)

    return False


def _contains_status_field(value):
    if isinstance(value, str):
        return _normalize_token(value) in {"status", "state"}

    if isinstance(value, Mapping):
        return any(_normalize_token(key) in {"status", "state"} for key in value)

    if isinstance(value, (list, tuple, set, frozenset)):
        return any(_contains_status_field(item) for item in value)

    return False


def _first_value(contexts, keys):
    for context in contexts:
        if not isinstance(context, Mapping):
            continue
        for key in keys:
            if key in context and context[key] is not None:
                return context[key]
    return None


def _nested_first_value(contexts, paths):
    for context in contexts:
        if not isinstance(context, Mapping):
            continue
        for path in paths:
            value = context
            for key in path:
                if not isinstance(value, Mapping) or key not in value:
                    value = None
                    break
                value = value[key]
            if value is not None:
                return value
    return None


def _string_value(value):
    if value is None:
        return None
    text = str(value).strip()
    return text or None


def _normalize_words(value):
    text = _string_value(value)
    if text is None:
        return None

    words = re.sub(r"([a-z0-9])([A-Z])", r"\1 \2", text)
    words = re.sub(r"[^A-Za-z0-9]+", " ", words)
    return " ".join(words.lower().split())


def _normalize_token(value):
    words = _normalize_words(value)
    if words is None:
        return ""
    return words.replace(" ", "")
