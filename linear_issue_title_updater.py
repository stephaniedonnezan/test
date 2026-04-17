#!/usr/bin/env python3
"""Update Linear issue titles when issues move to "to research".

The script expects a JSON payload from one of:
1. stdin
2. `AUTOMATION_TRIGGER_INFO` environment variable
3. `--payload-file` argument

If the event represents an issue status change to "to research", the script
updates the issue title by prefixing "Cursor researching - " (once) and calls
Linear's GraphQL API using `LINEAR_API_KEY`.
"""

from __future__ import annotations

import argparse
import json
import os
import sys
import urllib.error
import urllib.request

LINEAR_GRAPHQL_URL = "https://api.linear.app/graphql"
RESEARCH_STATUS = "to research"
TITLE_PREFIX = "Cursor researching"


def _normalize_status(value: str | None) -> str:
    return (value or "").strip().lower()


def should_update_title(trigger_context: dict) -> bool:
    """Return True when event is a status change to 'to research'."""
    if not isinstance(trigger_context, dict):
        return False

    trigger = (trigger_context.get("trigger") or "").strip().lower()
    new_status = _normalize_status(trigger_context.get("newStatus"))
    status = _normalize_status(trigger_context.get("status"))
    status_type = _normalize_status(trigger_context.get("statusType"))

    return (
        trigger == "status_changed"
        and (
            new_status == RESEARCH_STATUS
            or status == RESEARCH_STATUS
            or status_type == RESEARCH_STATUS
        )
    )


def get_updated_title(current_title: str) -> str:
    """Prefix title with 'Cursor researching' exactly once."""
    title = (current_title or "").strip()
    if not title:
        return TITLE_PREFIX

    if title.lower().startswith(TITLE_PREFIX.lower()):
        return title

    return f"{TITLE_PREFIX} - {title}"


def _load_payload_from_sources(payload_file: str | None) -> dict:
    if payload_file:
        with open(payload_file, "r", encoding="utf-8") as handle:
            return json.load(handle)

    env_payload = os.environ.get("AUTOMATION_TRIGGER_INFO")
    if env_payload:
        return json.loads(env_payload)

    stdin_data = sys.stdin.read().strip()
    if stdin_data:
        return json.loads(stdin_data)

    raise ValueError("No payload provided (stdin, AUTOMATION_TRIGGER_INFO, or --payload-file).")


def _linear_graphql_request(api_key: str, query: str, variables: dict) -> dict:
    body = json.dumps({"query": query, "variables": variables}).encode("utf-8")
    request = urllib.request.Request(
        LINEAR_GRAPHQL_URL,
        data=body,
        method="POST",
        headers={
            "Authorization": api_key,
            "Content-Type": "application/json",
        },
    )

    try:
        with urllib.request.urlopen(request, timeout=30) as response:
            response_body = response.read().decode("utf-8")
    except urllib.error.HTTPError as exc:
        message = exc.read().decode("utf-8", errors="replace")
        raise RuntimeError(f"Linear API HTTPError {exc.code}: {message}") from exc
    except urllib.error.URLError as exc:
        raise RuntimeError(f"Linear API URLError: {exc}") from exc

    data = json.loads(response_body)
    errors = data.get("errors")
    if errors:
        raise RuntimeError(f"Linear API returned errors: {errors}")
    return data


def update_linear_issue_title(api_key: str, issue_id: str, new_title: str) -> bool:
    mutation = """
    mutation UpdateIssueTitle($id: String!, $title: String!) {
      issueUpdate(id: $id, input: { title: $title }) {
        success
      }
    }
    """
    result = _linear_graphql_request(
        api_key=api_key,
        query=mutation,
        variables={"id": issue_id, "title": new_title},
    )
    return bool(result.get("data", {}).get("issueUpdate", {}).get("success"))


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--payload-file", help="Path to JSON payload file", default=None)
    args = parser.parse_args()

    payload = _load_payload_from_sources(args.payload_file)
    trigger_context = payload.get("triggerContext", {})

    if not should_update_title(trigger_context):
        print("No title update needed for this status change.")
        return 0

    issue_id = (trigger_context.get("id") or "").strip()
    title = trigger_context.get("title") or ""
    if not issue_id:
        raise ValueError("Missing triggerContext.id")

    updated_title = get_updated_title(title)
    if updated_title == title:
        print("Title already contains research prefix.")
        return 0

    api_key = os.environ.get("LINEAR_API_KEY")
    if not api_key:
        raise ValueError("Missing LINEAR_API_KEY environment variable")

    success = update_linear_issue_title(api_key=api_key, issue_id=issue_id, new_title=updated_title)
    if not success:
        raise RuntimeError("Linear issueUpdate mutation returned unsuccessful result.")

    print(f"Updated issue {issue_id} title to: {updated_title}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
