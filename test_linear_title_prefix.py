import json
import subprocess
import sys
import unittest

from linear_title_prefix import build_issue_title_update


class BuildIssueTitleUpdateTest(unittest.TestCase):
    def test_prefixes_flat_cursor_trigger_context_for_to_research_status(self):
        event = {
            "triggerContext": {
                "trigger": "status_changed",
                "newStatus": "To Research",
                "id": "POI-5037",
                "title": "Able to delete supply contracts with connected meter readings",
            }
        }

        self.assertEqual(
            build_issue_title_update(event),
            {
                "action": "update_issue_title",
                "issueId": "POI-5037",
                "title": (
                    "Cursor researching: Able to delete supply contracts with "
                    "connected meter readings"
                ),
            },
        )

    def test_ignores_other_statuses(self):
        event = {
            "triggerContext": {
                "trigger": "status_changed",
                "newStatus": "In Progress",
                "id": "POI-5037",
                "title": "Able to delete supply contracts",
            }
        }

        self.assertIsNone(build_issue_title_update(event))

    def test_ignores_non_status_change_triggers(self):
        event = {
            "triggerContext": {
                "trigger": "comment_created",
                "newStatus": "To Research",
                "id": "POI-5037",
                "title": "Able to delete supply contracts",
            }
        }

        self.assertIsNone(build_issue_title_update(event))

    def test_skips_duplicate_prefix_case_insensitively(self):
        event = {
            "trigger": "statusChanged",
            "newStatus": "to research",
            "id": "POI-5037",
            "title": "cursor researching: Able to delete supply contracts",
        }

        self.assertEqual(
            build_issue_title_update(event),
            {
                "action": "update_issue_title",
                "issueId": "POI-5037",
                "title": "cursor researching: Able to delete supply contracts",
            },
        )

    def test_normalizes_status_separators_and_camel_case(self):
        for status in ("to_research", "to-research", "toResearch", "TO RESEARCH"):
            with self.subTest(status=status):
                event = {
                    "trigger": "status_changed",
                    "newStatus": status,
                    "id": "POI-5037",
                    "title": "Able to delete supply contracts",
                }

                self.assertEqual(
                    build_issue_title_update(event)["title"],
                    "Cursor researching: Able to delete supply contracts",
                )

    def test_accepts_nested_linear_issue_update_payload(self):
        event = {
            "action": "update",
            "updatedFields": ["state"],
            "data": {
                "identifier": "POI-5037",
                "title": "Able to delete supply contracts",
                "state": {"name": "To Research"},
            },
        }

        self.assertEqual(
            build_issue_title_update(event),
            {
                "action": "update_issue_title",
                "issueId": "POI-5037",
                "title": "Cursor researching: Able to delete supply contracts",
            },
        )

    def test_accepts_changes_status_payload(self):
        event = {
            "type": "Issue Updated",
            "changes": {
                "status": {"name": "To Research"},
            },
            "issue": {
                "key": "POI-5037",
                "title": "Able to delete supply contracts",
            },
        }

        self.assertEqual(
            build_issue_title_update(event),
            {
                "action": "update_issue_title",
                "issueId": "POI-5037",
                "title": "Cursor researching: Able to delete supply contracts",
            },
        )

    def test_prefers_human_readable_identifier_over_uuid_id(self):
        event = {
            "trigger": "status_changed",
            "newStatus": "To Research",
            "id": "3d7c67d6-3bd4-4c6b-b96e-bcf755a6d4cc",
            "identifier": "POI-5037",
            "title": "Able to delete supply contracts",
        }

        self.assertEqual(build_issue_title_update(event)["issueId"], "POI-5037")

    def test_trims_issue_id_and_title(self):
        event = {
            "trigger": "status_changed",
            "newStatus": "To Research",
            "issueId": " POI-5037 ",
            "title": " Able to delete supply contracts ",
        }

        self.assertEqual(
            build_issue_title_update(event),
            {
                "action": "update_issue_title",
                "issueId": "POI-5037",
                "title": "Cursor researching: Able to delete supply contracts",
            },
        )

    def test_returns_none_when_issue_id_or_title_missing(self):
        self.assertIsNone(
            build_issue_title_update(
                {
                    "trigger": "status_changed",
                    "newStatus": "To Research",
                    "title": "Able to delete supply contracts",
                }
            )
        )
        self.assertIsNone(
            build_issue_title_update(
                {
                    "trigger": "status_changed",
                    "newStatus": "To Research",
                    "id": "POI-5037",
                }
            )
        )

    def test_cli_outputs_update_action_for_matching_payload(self):
        event = {
            "triggerContext": {
                "trigger": "status_changed",
                "newStatus": "To Research",
                "id": "POI-5037",
                "title": "Able to delete supply contracts",
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
                "issueId": "POI-5037",
                "title": "Cursor researching: Able to delete supply contracts",
            },
        )


if __name__ == "__main__":
    unittest.main()
