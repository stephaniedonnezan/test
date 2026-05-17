#!/usr/bin/env python3
"""Update Linear issue titles when issues move to the research status.

The script accepts a Linear/Cursor automation webhook payload as JSON on stdin
or from a file path. If the payload represents an issue status change into
"to research", it prefixes the issue title with "Cursor researching".
"""

from __future__ import annotations

import argparse
import json
import os
import re
import sys
import urllib.error
import urllib.request
from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from typing import Any


TITLE_PREFIX = "Cursor researching"
TARGET_STATUS = "to research"
LINEAR_GRAPHQL_URL = "https://api.linear.app/graphql"
STATUS_FIELDS = {
    "state",
    "state id",
    "state name",
    "status",
    "workflow state",
}
STATUS_FIELD_TOKENS = {field.replace(" ", "") for field in STATUS_FIELDS}
STATUS_CHANGE_MARKERS = {
    "state change",
    "state changed",
    "status change",
    "status changed",
    "workflow state change",
    "workflow state changed",
}
UPDATE_MARKERS = {
    "issue update",
    "issue updated",
    "update",
    "updated",
    "updated issue",
}


@dataclass(frozen=True)
class IssueEvent:
    issue_id: str
    title: str
    new_status: str | None
    is_status_change: bool


@dataclass(frozen=True)
class TitleUpdate:
    issue_id: str
    current_title: str
    new_title: str
    new_status: str


class LinearApiError(RuntimeError):
    """Raised when Linear rejects the GraphQL request."""


def build_title_update(payload: Mapping[str, Any]) -> TitleUpdate | None:
    """Return the title update required by a matching research status change."""

    event = extract_issue_event(payload)
    if event is None:
        return None

    if not event.is_status_change:
        return None

    if normalize_phrase(event.new_status) != TARGET_STATUS:
        return None

    new_title = add_research_prefix(event.title)
    if new_title == event.title.strip():
        return None

    return TitleUpdate(
        issue_id=event.issue_id,
        current_title=event.title,
        new_title=new_title,
        new_status=event.new_status or "",
    )


def extract_issue_event(payload: Mapping[str, Any]) -> IssueEvent | None:
    """Extract issue metadata from common Cursor and Linear webhook shapes."""

    if not isinstance(payload, Mapping):
        return None

    contexts = candidate_contexts(payload)
    issue_id = first_path_string(
        contexts,
        ("linearId",),
        ("linear_id",),
        ("issueId",),
        ("issue_id",),
        ("id",),
        ("identifier",),
    )
    title = first_path_string(contexts, ("title",))

    if not issue_id or title is None:
        return None

    return IssueEvent(
        issue_id=issue_id.strip(),
        title=title,
        new_status=extract_new_status(contexts),
        is_status_change=is_status_change_event(contexts),
    )


def candidate_contexts(payload: Mapping[str, Any]) -> list[Mapping[str, Any]]:
    """Return payload mappings ordered from most to least trigger-specific."""

    contexts: list[Mapping[str, Any]] = []

    def add(value: Any) -> None:
        if isinstance(value, Mapping) and value not in contexts:
            contexts.append(value)

    trigger_context = payload.get("triggerContext")
    add(trigger_context)
    if isinstance(trigger_context, Mapping):
        for key in ("data", "issue", "node", "payload"):
            add(trigger_context.get(key))

    add(payload)
    for key in ("data", "issue", "node", "payload"):
        nested = payload.get(key)
        add(nested)
        if isinstance(nested, Mapping):
            for nested_key in ("data", "issue", "node", "payload"):
                add(nested.get(nested_key))

    return contexts


def is_status_change_event(contexts: Sequence[Mapping[str, Any]]) -> bool:
    markers = [
        context.get(key)
        for context in contexts
        for key in ("trigger", "webhookType", "webhook_type", "action", "type", "event")
    ]

    normalized_markers = {normalize_phrase(marker) for marker in markers}
    if normalized_markers & STATUS_CHANGE_MARKERS:
        return True

    normalized_marker_tokens = {marker.replace(" ", "") for marker in normalized_markers}
    if normalized_marker_tokens & {marker.replace(" ", "") for marker in STATUS_CHANGE_MARKERS}:
        return True

    if normalized_markers & UPDATE_MARKERS:
        return updated_fields_include_status(contexts)

    return False


def updated_fields_include_status(contexts: Sequence[Mapping[str, Any]]) -> bool:
    for context in contexts:
        updated_from = context.get("updatedFrom") or context.get("updated_from")
        if isinstance(updated_from, Mapping):
            if any(is_status_field(field) for field in updated_from):
                return True

        for key in ("updatedFields", "updated_fields", "changedFields", "changed_fields"):
            fields = context.get(key)
            if isinstance(fields, str):
                field_names = [fields]
            elif isinstance(fields, Sequence) and not isinstance(
                fields, (bytes, bytearray, str)
            ):
                field_names = [str(field) for field in fields]
            else:
                continue

            if any(is_status_field(field) for field in field_names):
                return True

    return False


def is_status_field(value: Any) -> bool:
    phrase = normalize_phrase(value)
    return phrase in STATUS_FIELDS or phrase.replace(" ", "") in STATUS_FIELD_TOKENS


def extract_new_status(contexts: Sequence[Mapping[str, Any]]) -> str | None:
    explicit_status = first_path_string(
        contexts,
        ("newStatus",),
        ("new_status",),
        ("newState",),
        ("new_state",),
        ("toStatus",),
        ("to_status",),
        ("toState",),
        ("to_state",),
    )
    if explicit_status:
        return explicit_status

    return first_path_string(
        contexts,
        ("status", "name"),
        ("state", "name"),
        ("workflowState", "name"),
        ("workflow_state", "name"),
        ("status",),
        ("state",),
        ("stateName",),
        ("state_name",),
        ("workflowState",),
        ("workflow_state",),
    )


def first_path_string(
    contexts: Sequence[Mapping[str, Any]],
    *paths: tuple[str, ...],
) -> str | None:
    for path in paths:
        for context in contexts:
            value = lookup_path(context, path)
            if isinstance(value, str) and value.strip():
                return value
    return None


def lookup_path(mapping: Mapping[str, Any], path: Sequence[str]) -> Any:
    current: Any = mapping
    for key in path:
        if not isinstance(current, Mapping):
            return None
        current = current.get(key)
    return current


def has_research_prefix(title: str) -> bool:
    return normalize_phrase(title).startswith(TARGET_PREFIX_PHRASE)


def add_research_prefix(title: str) -> str:
    stripped_title = title.strip()
    if has_research_prefix(stripped_title):
        return stripped_title
    if not stripped_title:
        return TITLE_PREFIX
    return f"{TITLE_PREFIX}: {stripped_title}"


def normalize_phrase(value: Any) -> str:
    if not isinstance(value, str):
        return ""

    words = re.sub(r"(?<=[a-z0-9])(?=[A-Z])", " ", value).strip()
    words = re.sub(r"[^a-zA-Z0-9]+", " ", words).strip().lower()
    return re.sub(r"\s+", " ", words)


TARGET_PREFIX_PHRASE = normalize_phrase(TITLE_PREFIX)


def read_payload(payload_file: str | None) -> Mapping[str, Any]:
    if payload_file:
        with open(payload_file, "r", encoding="utf-8") as handle:
            payload = json.load(handle)
    else:
        payload = json.load(sys.stdin)

    if not isinstance(payload, Mapping):
        raise ValueError("Webhook payload must be a JSON object")
    return payload


class LinearClient:
    def __init__(
        self,
        api_key: str,
        endpoint: str = LINEAR_GRAPHQL_URL,
    ) -> None:
        self.api_key = api_key
        self.endpoint = endpoint

    def update_issue_title(self, issue_id: str, title: str) -> None:
        query = """
        mutation UpdateIssueTitle($id: String!, $title: String!) {
          issueUpdate(id: $id, input: { title: $title }) {
            success
            issue {
              id
              identifier
              title
            }
          }
        }
        """
        response = self.execute(query, {"id": issue_id, "title": title})
        issue_update = response.get("issueUpdate")
        if not isinstance(issue_update, Mapping) or not issue_update.get("success"):
            raise LinearApiError("Linear did not confirm the issue title update")

    def execute(self, query: str, variables: Mapping[str, Any]) -> Mapping[str, Any]:
        body = json.dumps({"query": query, "variables": variables}).encode("utf-8")
        request = urllib.request.Request(
            self.endpoint,
            data=body,
            headers={
                "Authorization": self.api_key,
                "Content-Type": "application/json",
            },
            method="POST",
        )

        try:
            with urllib.request.urlopen(request, timeout=20) as response:
                response_body = response.read()
        except urllib.error.HTTPError as error:
            details = error.read().decode("utf-8", errors="replace")
            raise LinearApiError(
                f"Linear API request failed with HTTP {error.code}: {details}"
            ) from error
        except urllib.error.URLError as error:
            raise LinearApiError(f"Linear API request failed: {error.reason}") from error

        decoded = json.loads(response_body)
        if not isinstance(decoded, Mapping):
            raise LinearApiError("Linear API returned a non-object response")
        if decoded.get("errors"):
            raise LinearApiError(f"Linear API returned errors: {decoded['errors']}")

        data = decoded.get("data")
        if not isinstance(data, Mapping):
            raise LinearApiError("Linear API response did not include data")
        return data


def parse_args(argv: list[str]) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description=(
            "Prefix Linear issue titles with 'Cursor researching' when a status "
            "change moves the issue to 'to research'."
        )
    )
    parser.add_argument(
        "--payload-file",
        help="Path to a JSON webhook payload. Reads stdin when omitted.",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Print the planned update without calling the Linear API.",
    )
    parser.add_argument(
        "--api-key-env",
        default="LINEAR_API_KEY",
        help="Environment variable containing the Linear API key.",
    )
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv or sys.argv[1:])
    payload = read_payload(args.payload_file)
    update = build_title_update(payload)

    if update is None:
        print("No Linear title update needed.")
        return 0

    print(
        "Linear issue "
        f"{update.issue_id} moved to {update.new_status!r}; "
        f"title will become {update.new_title!r}."
    )

    if args.dry_run:
        return 0

    api_key = os.environ.get(args.api_key_env)
    if not api_key:
        raise ValueError(f"Missing Linear API key in ${args.api_key_env}")

    LinearClient(api_key).update_issue_title(update.issue_id, update.new_title)
    print("Linear issue title updated.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
