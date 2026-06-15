import json
import subprocess
import sys
import unittest

from linear_title_prefix import (
    RESEARCH_TITLE_PREFIX,
    build_issue_title_update,
    derive_updated_title,
    update_issue_title_for_status,
)


class UpdateIssueTitleForStatusTests(unittest.TestCase):
    def test_prefixes_title_for_to_research_status(self) -> None:
        updated_title = update_issue_title_for_status("Issues indicator is mispositioned", "to research")

        self.assertEqual(updated_title, "Cursor researching: Issues indicator is mispositioned")

    def test_status_match_is_case_and_whitespace_insensitive(self) -> None:
        updated_title = update_issue_title_for_status("Investigate loading state", "  TO   RESEARCH  ")

        self.assertEqual(updated_title, "Cursor researching: Investigate loading state")

    def test_returns_none_for_other_statuses(self) -> None:
        self.assertIsNone(update_issue_title_for_status("Investigate loading state", "In Review"))

    def test_returns_none_when_title_already_has_prefix(self) -> None:
        title = f"{RESEARCH_TITLE_PREFIX}: Investigate loading state"

        self.assertIsNone(update_issue_title_for_status(title, "to research"))

    def test_returns_none_for_blank_title(self) -> None:
        self.assertIsNone(update_issue_title_for_status("   ", "to research"))


class BuildIssueTitleUpdateTests(unittest.TestCase):
    def test_builds_update_for_cursor_trigger_context(self) -> None:
        payload = {
            "triggerContext": {
                "triggerType": "linear",
                "webhookType": "issue",
                "trigger": "status_changed",
                "newStatus": "to research",
                "title": "Issues indicator is mispositioned in container logic view",
                "id": "POI-4935",
            }
        }

        self.assertEqual(
            build_issue_title_update(payload),
            {
                "action": "update_issue_title",
                "issueId": "POI-4935",
                "title": "Cursor researching: Issues indicator is mispositioned in container logic view",
            },
        )

    def test_returns_none_when_cursor_trigger_context_status_is_not_to_research(self) -> None:
        payload = {
            "triggerContext": {
                "triggerType": "linear",
                "webhookType": "issue",
                "trigger": "status_changed",
                "newStatus": "In Review",
                "title": "Issues indicator is mispositioned in container logic view",
                "id": "POI-4935",
            }
        }

        self.assertIsNone(build_issue_title_update(payload))

    def test_returns_none_for_non_status_change_trigger(self) -> None:
        payload = {
            "triggerContext": {
                "triggerType": "linear",
                "webhookType": "issue",
                "trigger": "comment_created",
                "newStatus": "to research",
                "title": "Investigate loading state",
                "id": "POI-100",
            }
        }

        self.assertIsNone(build_issue_title_update(payload))

    def test_supports_raw_payload_without_trigger_metadata(self) -> None:
        payload = {
            "issueId": "POI-101",
            "status": "to research",
            "title": "Investigate loading state",
        }

        self.assertEqual(
            build_issue_title_update(payload),
            {
                "action": "update_issue_title",
                "issueId": "POI-101",
                "title": "Cursor researching: Investigate loading state",
            },
        )

    def test_supports_nested_linear_issue_update_payload(self) -> None:
        payload = {
            "type": "Issue",
            "action": "update",
            "updatedFields": ["state"],
            "data": {
                "id": "issue-uuid",
                "identifier": "POI-102",
                "title": "Investigate stale container count",
                "state": {"name": "to research"},
            },
        }

        self.assertEqual(
            build_issue_title_update(payload),
            {
                "action": "update_issue_title",
                "issueId": "issue-uuid",
                "title": "Cursor researching: Investigate stale container count",
            },
        )

    def test_supports_changed_status_value(self) -> None:
        payload = {
            "id": "POI-103",
            "title": "Investigate stale container count",
            "changes": {"status": {"from": "Backlog", "to": "to research"}},
        }

        self.assertEqual(
            derive_updated_title(payload),
            "Cursor researching: Investigate stale container count",
        )

    def test_returns_none_without_issue_id(self) -> None:
        payload = {"status": "to research", "title": "Investigate loading state"}

        self.assertIsNone(build_issue_title_update(payload))


class CommandLineTests(unittest.TestCase):
    def test_cli_outputs_update_action(self) -> None:
        payload = {
            "triggerContext": {
                "trigger": "status_changed",
                "newStatus": "to research",
                "title": "Investigate loading state",
                "id": "POI-104",
            }
        }

        result = subprocess.run(
            [sys.executable, "linear_title_prefix.py"],
            input=json.dumps(payload),
            text=True,
            capture_output=True,
            check=True,
        )

        self.assertEqual(
            json.loads(result.stdout),
            {
                "action": "update_issue_title",
                "issueId": "POI-104",
                "title": "Cursor researching: Investigate loading state",
            },
        )


if __name__ == "__main__":
    unittest.main()
