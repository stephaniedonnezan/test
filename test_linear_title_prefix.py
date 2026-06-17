import json
import subprocess
import sys
import unittest

from linear_title_prefix import build_issue_title_update


class LinearTitlePrefixTest(unittest.TestCase):
    def test_prefixes_flat_status_changed_payload_entering_to_research(self):
        event = {
            "trigger": "status_changed",
            "newStatus": "To Research",
            "id": "POI-5013",
            "title": "Loading message goes behind Mass Balance items",
        }

        self.assertEqual(
            build_issue_title_update(event),
            {
                "action": "update_issue_title",
                "issueId": "POI-5013",
                "title": (
                    "Cursor researching: "
                    "Loading message goes behind Mass Balance items"
                ),
            },
        )

    def test_prefixes_nested_cursor_trigger_context(self):
        event = {
            "triggerContext": {
                "trigger": "status_changed",
                "newStatus": "to_research",
                "id": "POI-5013",
                "title": "Loading message goes behind Mass Balance items",
            }
        }

        self.assertEqual(
            build_issue_title_update(event),
            {
                "action": "update_issue_title",
                "issueId": "POI-5013",
                "title": (
                    "Cursor researching: "
                    "Loading message goes behind Mass Balance items"
                ),
            },
        )

    def test_prefixes_linear_update_payload_with_state_marker(self):
        event = {
            "action": "update",
            "type": "Issue",
            "updatedFields": ["state"],
            "data": {
                "identifier": "POI-5013",
                "title": "Loading message goes behind Mass Balance items",
                "state": {"name": "To Research"},
            },
        }

        self.assertEqual(
            build_issue_title_update(event),
            {
                "action": "update_issue_title",
                "issueId": "POI-5013",
                "title": (
                    "Cursor researching: "
                    "Loading message goes behind Mass Balance items"
                ),
            },
        )

    def test_prefixes_status_from_changes_new_value(self):
        event = {
            "action": "Issue Updated",
            "changes": {"workflowState": {"newValue": {"name": "toResearch"}}},
            "issue": {
                "id": "issue-uuid",
                "title": "Loading message goes behind Mass Balance items",
            },
        }

        self.assertEqual(
            build_issue_title_update(event),
            {
                "action": "update_issue_title",
                "issueId": "issue-uuid",
                "title": (
                    "Cursor researching: "
                    "Loading message goes behind Mass Balance items"
                ),
            },
        )

    def test_ignores_other_statuses(self):
        event = {
            "trigger": "status_changed",
            "newStatus": "Todo",
            "id": "POI-5013",
            "title": "Loading message goes behind Mass Balance items",
        }

        self.assertIsNone(build_issue_title_update(event))

    def test_ignores_non_status_triggers(self):
        event = {
            "trigger": "comment_created",
            "newStatus": "To Research",
            "id": "POI-5013",
            "title": "Loading message goes behind Mass Balance items",
        }

        self.assertIsNone(build_issue_title_update(event))

    def test_ignores_already_prefixed_titles(self):
        event = {
            "trigger": "status_changed",
            "newStatus": "To Research",
            "id": "POI-5013",
            "title": (
                "cursor researching: "
                "Loading message goes behind Mass Balance items"
            ),
        }

        self.assertIsNone(build_issue_title_update(event))

    def test_ignores_missing_issue_id_or_title(self):
        self.assertIsNone(
            build_issue_title_update(
                {"trigger": "status_changed", "newStatus": "To Research"}
            )
        )
        self.assertIsNone(
            build_issue_title_update(
                {
                    "trigger": "status_changed",
                    "newStatus": "To Research",
                    "id": "POI-5013",
                }
            )
        )

    def test_ignores_non_mapping_payloads(self):
        self.assertIsNone(build_issue_title_update(None))
        self.assertIsNone(build_issue_title_update(["not", "a", "mapping"]))

    def test_cli_prints_update_action(self):
        event = {
            "triggerContext": {
                "trigger": "status_changed",
                "newStatus": "To Research",
                "id": "POI-5013",
                "title": "Loading message goes behind Mass Balance items",
            }
        }

        result = subprocess.run(
            [sys.executable, "linear_title_prefix.py"],
            input=json.dumps(event),
            text=True,
            capture_output=True,
            check=True,
        )

        self.assertEqual(
            json.loads(result.stdout),
            {
                "action": "update_issue_title",
                "issueId": "POI-5013",
                "title": (
                    "Cursor researching: "
                    "Loading message goes behind Mass Balance items"
                ),
            },
        )


if __name__ == "__main__":
    unittest.main()
