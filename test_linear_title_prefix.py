import json
import subprocess
import sys
import unittest

from linear_title_prefix import build_issue_title_update


class LinearTitlePrefixTests(unittest.TestCase):
    def test_flat_automation_status_changed_to_research_adds_prefix(self):
        event = {
            "triggerContext": {
                "trigger": "status_changed",
                "newStatus": "To Research",
                "id": "POI-4775",
                "title": "Mass balance shows non-zero grid mix",
            }
        }

        self.assertEqual(
            build_issue_title_update(event),
            {
                "action": "update_issue_title",
                "issueId": "POI-4775",
                "title": "Cursor researching: Mass balance shows non-zero grid mix",
            },
        )

    def test_current_canceled_status_does_not_update_title(self):
        event = {
            "triggerContext": {
                "trigger": "status_changed",
                "newStatus": "Canceled",
                "status": "Canceled",
                "id": "POI-4775",
                "title": "Mass balance shows non-zero grid mix",
            }
        }

        self.assertIsNone(build_issue_title_update(event))

    def test_non_status_trigger_does_not_update_title(self):
        event = {
            "triggerContext": {
                "trigger": "comment_created",
                "newStatus": "To Research",
                "id": "POI-4775",
                "title": "Mass balance shows non-zero grid mix",
            }
        }

        self.assertIsNone(build_issue_title_update(event))

    def test_already_prefixed_title_does_not_duplicate_prefix(self):
        event = {
            "triggerContext": {
                "trigger": "statusChanged",
                "newStatus": "to_research",
                "id": "POI-4775",
                "title": "cursor researching: Mass balance shows non-zero grid mix",
            }
        }

        self.assertIsNone(build_issue_title_update(event))

    def test_status_normalization_accepts_camel_case_status(self):
        event = {
            "triggerContext": {
                "trigger": "statusChanged",
                "newStatus": "toResearch",
                "id": "POI-4775",
                "title": "Mass balance shows non-zero grid mix",
            }
        }

        self.assertEqual(
            build_issue_title_update(event)["title"],
            "Cursor researching: Mass balance shows non-zero grid mix",
        )

    def test_nested_linear_issue_update_uses_state_name_when_updated_fields_include_state(self):
        event = {
            "action": "update",
            "type": "Issue",
            "updatedFields": ["state"],
            "data": {
                "id": "POI-4775",
                "title": "Mass balance shows non-zero grid mix",
                "state": {"name": "To Research"},
            },
        }

        self.assertEqual(
            build_issue_title_update(event),
            {
                "action": "update_issue_title",
                "issueId": "POI-4775",
                "title": "Cursor researching: Mass balance shows non-zero grid mix",
            },
        )

    def test_issue_update_without_status_field_does_not_update_title(self):
        event = {
            "action": "update",
            "type": "Issue",
            "updatedFields": ["description"],
            "data": {
                "id": "POI-4775",
                "title": "Mass balance shows non-zero grid mix",
                "state": {"name": "To Research"},
            },
        }

        self.assertIsNone(build_issue_title_update(event))

    def test_missing_issue_title_or_id_does_not_update_title(self):
        event = {
            "triggerContext": {
                "trigger": "status_changed",
                "newStatus": "To Research",
                "title": "Mass balance shows non-zero grid mix",
            }
        }

        self.assertIsNone(build_issue_title_update(event))

    def test_cli_outputs_json_action_for_matching_payload(self):
        event = {
            "triggerContext": {
                "trigger": "status_changed",
                "newStatus": "To Research",
                "id": "POI-4775",
                "title": "Mass balance shows non-zero grid mix",
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
                "issueId": "POI-4775",
                "title": "Cursor researching: Mass balance shows non-zero grid mix",
            },
        )


if __name__ == "__main__":
    unittest.main()
