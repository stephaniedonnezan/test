import json
import subprocess
import sys
import unittest

from linear_title_prefix import build_issue_title_update


class BuildIssueTitleUpdateTest(unittest.TestCase):
    def test_prefixes_flat_cursor_status_change_to_research(self):
        result = build_issue_title_update(
            {
                "trigger": "status_changed",
                "newStatus": "to research",
                "id": "POI-5010",
                "title": "Mass balance execution (monthly operations)",
            }
        )

        self.assertEqual(
            result,
            {
                "action": "update_issue_title",
                "issueId": "POI-5010",
                "title": "Cursor researching: Mass balance execution (monthly operations)",
            },
        )

    def test_accepts_nested_trigger_context(self):
        result = build_issue_title_update(
            {
                "triggerContext": {
                    "trigger": "statusChanged",
                    "newStatus": "To Research",
                    "id": "POI-5010",
                    "title": "Mass balance execution",
                }
            }
        )

        self.assertEqual(result["title"], "Cursor researching: Mass balance execution")

    def test_accepts_normalized_status_name_variants(self):
        result = build_issue_title_update(
            {
                "trigger": "status_changed",
                "new_status": "to-research",
                "issueId": "POI-5010",
                "title": "Mass balance execution",
            }
        )

        self.assertEqual(result["issueId"], "POI-5010")

    def test_accepts_nested_linear_issue_update_payload(self):
        result = build_issue_title_update(
            {
                "action": "update",
                "updatedFields": ["state"],
                "data": {
                    "id": "POI-5010",
                    "title": "Mass balance execution",
                    "state": {"name": "To Research"},
                },
            }
        )

        self.assertEqual(result["title"], "Cursor researching: Mass balance execution")

    def test_accepts_status_change_from_changes_payload(self):
        result = build_issue_title_update(
            {
                "action": "update",
                "data": {"issue": {"identifier": "POI-5010", "title": "Mass balance execution"}},
                "changes": {"state": {"from": {"name": "Backlog"}, "to": {"name": "To Research"}}},
            }
        )

        self.assertEqual(result["issueId"], "POI-5010")

    def test_ignores_other_statuses(self):
        result = build_issue_title_update(
            {
                "trigger": "status_changed",
                "newStatus": "Agent research to review",
                "id": "POI-5010",
                "title": "Mass balance execution",
            }
        )

        self.assertIsNone(result)

    def test_ignores_non_status_triggers(self):
        result = build_issue_title_update(
            {
                "trigger": "comment_created",
                "newStatus": "to research",
                "id": "POI-5010",
                "title": "Mass balance execution",
            }
        )

        self.assertIsNone(result)

    def test_ignores_existing_prefix_case_insensitively(self):
        result = build_issue_title_update(
            {
                "trigger": "status_changed",
                "newStatus": "to research",
                "id": "POI-5010",
                "title": "cursor researching: Mass balance execution",
            }
        )

        self.assertIsNone(result)

    def test_requires_issue_id_and_title(self):
        self.assertIsNone(
            build_issue_title_update({"trigger": "status_changed", "newStatus": "to research", "id": "POI-5010"})
        )
        self.assertIsNone(
            build_issue_title_update(
                {"trigger": "status_changed", "newStatus": "to research", "title": "Mass balance execution"}
            )
        )

    def test_does_not_use_status_name_as_title(self):
        result = build_issue_title_update(
            {
                "trigger": "status_changed",
                "newStatus": "to research",
                "id": "POI-5010",
                "state": {"name": "To Research"},
            }
        )

        self.assertIsNone(result)

    def test_cli_prints_update_action(self):
        payload = {
            "trigger": "status_changed",
            "newStatus": "to research",
            "id": "POI-5010",
            "title": "Mass balance execution",
        }

        completed = subprocess.run(
            [sys.executable, "linear_title_prefix.py"],
            input=json.dumps(payload),
            text=True,
            check=True,
            capture_output=True,
        )

        self.assertEqual(json.loads(completed.stdout)["issueId"], "POI-5010")


if __name__ == "__main__":
    unittest.main()
