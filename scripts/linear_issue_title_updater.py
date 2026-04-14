"""Update Linear issue titles when status changes to "to research".

This script is designed for automation/webhook usage. It inspects a Linear
issue status-change payload and, when the new status is "to research",
prefixes the issue title with "Cursor researching" (if not already present).
"""

from __future__ import annotations

import argparse
import json
import os
import sys
import urllib.error
import urllib.request
from typing import Any

LINEAR_GRAPHQL_URL = "https://api.linear.app/graphql"
TITLE_PREFIX = "Cursor researching"
TARGET_STATUS = "to research"


def normalize_text(value: str | None) -> str:
    if value is None:
        return ""
    return value.strip().lower()


def title_has_prefix(title: str, prefix: str = TITLE_PREFIX) -> bool:
    return normalize_text(title).startswith(normalize_text(prefix))


def build_prefixed_title(title: str, prefix: str = TITLE_PREFIX) -> str:
    if title_has_prefix(title, prefix):
        return title
    return f"{prefix}: {title}"


def should_update_title(new_status: str | None, current_title: str | None) -> bool:
    if normalize_text(new_status) != TARGET_STATUS:
        return False
    if not current_title:
        return False
    return not title_has_prefix(current_title)


def build_title_update(payload: dict[str, Any]) -> dict[str, str] | None:
    trigger_context = payload.get("triggerContext") or {}
    status = trigger_context.get("newStatus")
    current_title = trigger_context.get("title")
    identifier = trigger_context.get("id")

    if not should_update_title(status, current_title):
        return None
    if not identifier:
        return None

    return {
        "identifier": identifier,
        "old_title": current_title,
        "new_title": build_prefixed_title(current_title),
    }


def linear_graphql_request(
    query: str,
    variables: dict[str, Any],
    api_key: str,
) -> dict[str, Any]:
    body = json.dumps({"query": query, "variables": variables}).encode("utf-8")
    request = urllib.request.Request(
        LINEAR_GRAPHQL_URL,
        data=body,
        headers={
            "Content-Type": "application/json",
            "Authorization": api_key,
        },
        method="POST",
    )

    try:
        with urllib.request.urlopen(request, timeout=30) as response:
            response_body = response.read().decode("utf-8")
    except urllib.error.HTTPError as exc:
        details = exc.read().decode("utf-8", errors="replace")
        raise RuntimeError(f"Linear API HTTP error: {exc.code} {details}") from exc
    except urllib.error.URLError as exc:
        raise RuntimeError(f"Linear API connection error: {exc}") from exc

    parsed = json.loads(response_body)
    if parsed.get("errors"):
        raise RuntimeError(f"Linear API returned errors: {parsed['errors']}")
    return parsed


def resolve_issue_id(identifier: str, api_key: str) -> str:
    query = """
    query ResolveIssueId($identifier: String!) {
      issue(identifier: $identifier) {
        id
      }
    }
    """
    result = linear_graphql_request(query, {"identifier": identifier}, api_key)
    issue = (result.get("data") or {}).get("issue")
    if not issue or not issue.get("id"):
        raise RuntimeError(f"Could not resolve issue identifier '{identifier}'")
    return issue["id"]


def update_issue_title_by_identifier(
    identifier: str,
    new_title: str,
    api_key: str,
) -> None:
    issue_id = resolve_issue_id(identifier, api_key)
    mutation = """
    mutation UpdateIssueTitle($id: String!, $title: String!) {
      issueUpdate(id: $id, input: { title: $title }) {
        success
      }
    }
    """
    result = linear_graphql_request(
        mutation,
        {"id": issue_id, "title": new_title},
        api_key,
    )
    success = (((result.get("data") or {}).get("issueUpdate") or {}).get("success"))
    if not success:
        raise RuntimeError(f"Linear issueUpdate failed for '{identifier}'")


def handle_event(payload: dict[str, Any], api_key: str, dry_run: bool = False) -> dict[str, Any]:
    update = build_title_update(payload)
    if update is None:
        return {"updated": False, "reason": "No matching status/title change"}

    if dry_run:
        return {"updated": False, "dry_run": True, **update}

    update_issue_title_by_identifier(
        identifier=update["identifier"],
        new_title=update["new_title"],
        api_key=api_key,
    )
    return {"updated": True, **update}


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Prefix Linear issue title when status changes to 'to research'."
    )
    parser.add_argument(
        "--payload-file",
        help="Path to the JSON payload. Reads stdin when omitted.",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Compute result without calling the Linear API.",
    )
    return parser.parse_args()


def load_payload(payload_file: str | None) -> dict[str, Any]:
    if payload_file:
        with open(payload_file, "r", encoding="utf-8") as file:
            return json.load(file)
    return json.load(sys.stdin)


def main() -> int:
    args = parse_args()
    payload = load_payload(args.payload_file)

    api_key = os.environ.get("LINEAR_API_KEY", "").strip()
    if not args.dry_run and not api_key:
        raise RuntimeError("LINEAR_API_KEY is required unless running with --dry-run")

    result = handle_event(payload, api_key=api_key, dry_run=args.dry_run)
    print(json.dumps(result, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
