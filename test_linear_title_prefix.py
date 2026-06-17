import json
import subprocess
import sys
import unittest

from linear_title_prefix import build_issue_title_update


class BuildIssueTitleUpdateTest(unittest.TestCase):
    def test_prefixes_flat_cursor_status_change_to_research(self) -> None:
        event = {
            "triggerContext": {
                "trigger": "status_changed",
                "webhookType": "issue",
                "newStatus": "To Research",
                "id": "POI-4989",
                "title": "0 stays in Site creation Dialogue despite adding a number",
            }
        }

        self.assertEqual(
            build_issue_title_update(event),
            {
                "action": "update_issue_title",
                "issueId": "POI-4989",
                "title": (
                    "Cursor researching: "
                    "0 stays in Site creation Dialogue despite adding a number"
                ),
            },
        )

    def test_ignores_status_change_to_other_status(self) -> None:
        event = {
            "triggerContext": {
                "trigger": "status_changed",
                "newStatus": "Todo",
                "id": "POI-4989",
                "title": "0 stays in Site creation Dialogue despite adding a number",
            }
        }

        self.assertIsNone(build_issue_title_update(event))

    def test_ignores_non_status_trigger(self) -> None:
        event = {
            "triggerContext": {
                "trigger": "comment_created",
                "newStatus": "To Research",
                "id": "POI-4989",
                "title": "0 stays in Site creation Dialogue despite adding a number",
            }
        }

        self.assertIsNone(build_issue_title_update(event))

    def test_ignores_existing_cursor_researching_prefix(self) -> None:
        event = {
            "triggerContext": {
                "trigger": "statusChanged",
                "newStatus": "to_research",
                "id": "POI-4989",
                "title": "cursor researching: Existing title",
            }
        }

        self.assertIsNone(build_issue_title_update(event))

    def test_supports_nested_linear_update_payload(self) -> None:
        event = {
            "action": "update",
            "updatedFields": ["state"],
            "data": {
                "issue": {
                    "identifier": "POI-4989",
                    "title": "Site creation dialogue keeps default zero",
                    "state": {"name": "To Research"},
                }
            },
        }

        self.assertEqual(
            build_issue_title_update(event),
            {
                "action": "update_issue_title",
                "issueId": "POI-4989",
                "title": "Cursor researching: Site creation dialogue keeps default zero",
            },
        )

    def test_supports_change_object_new_status(self) -> None:
        event = {
            "action": "Issue Updated",
            "changes": {"workflowState": {"from": "Todo", "to": "toResearch"}},
            "data": {
                "issue": {
                    "identifier": "POI-4989",
                    "title": "Site creation dialogue keeps default zero",
                }
            },
        }

        self.assertEqual(
            build_issue_title_update(event),
            {
                "action": "update_issue_title",
                "issueId": "POI-4989",
                "title": "Cursor researching: Site creation dialogue keeps default zero",
            },
        )

    def test_supports_change_list_new_status(self) -> None:
        event = {
            "action": "Issue Updated",
            "changes": [
                {
                    "field": "status",
                    "oldValue": "Todo",
                    "newValue": {"name": "to research"},
                }
            ],
            "data": {
                "issue": {
                    "identifier": "POI-4989",
                    "title": "Site creation dialogue keeps default zero",
                }
            },
        }

        self.assertEqual(
            build_issue_title_update(event),
            {
                "action": "update_issue_title",
                "issueId": "POI-4989",
                "title": "Cursor researching: Site creation dialogue keeps default zero",
            },
        )

    def test_ignores_generic_update_without_status_field_change(self) -> None:
        event = {
            "action": "update",
            "updatedFields": ["title"],
            "data": {
                "issue": {
                    "identifier": "POI-4989",
                    "title": "Site creation dialogue keeps default zero",
                    "state": {"name": "To Research"},
                }
            },
        }

        self.assertIsNone(build_issue_title_update(event))

    def test_requires_issue_id_and_title(self) -> None:
        event = {
            "triggerContext": {
                "trigger": "status_changed",
                "newStatus": "To Research",
                "id": "POI-4989",
            }
        }

        self.assertIsNone(build_issue_title_update(event))

    def test_cli_prints_update_action(self) -> None:
        event = {
            "triggerContext": {
                "trigger": "status_changed",
                "newStatus": "To Research",
                "id": "POI-4989",
                "title": "0 stays in Site creation Dialogue despite adding a number",
            }
        }

        completed = subprocess.run(
            [sys.executable, "linear_title_prefix.py"],
            input=json.dumps(event),
            text=True,
            capture_output=True,
            check=True,
        )

        self.assertEqual(
            json.loads(completed.stdout),
            {
                "action": "update_issue_title",
                "issueId": "POI-4989",
                "title": (
                    "Cursor researching: "
                    "0 stays in Site creation Dialogue despite adding a number"
                ),
            },
        )


if __name__ == "__main__":
    unittest.main()
