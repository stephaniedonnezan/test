import json
import subprocess
import sys
import unittest

from linear_title_prefix import build_issue_title_update


class BuildIssueTitleUpdateTest(unittest.TestCase):
    def test_prefixes_flat_automation_payload_for_to_research_status(self):
        payload = {
            "triggerContext": {
                "trigger": "status_changed",
                "newStatus": "To Research",
                "id": "POI-4588",
                "title": "Methane closing warnings are merging",
            }
        }

        self.assertEqual(
            build_issue_title_update(payload),
            {
                "action": "update_issue_title",
                "issueId": "POI-4588",
                "title": "Cursor researching: Methane closing warnings are merging",
            },
        )

    def test_returns_none_for_non_status_change_trigger(self):
        payload = {
            "triggerContext": {
                "trigger": "comment_created",
                "newStatus": "to research",
                "id": "POI-4588",
                "title": "Methane closing warnings are merging",
            }
        }

        self.assertIsNone(build_issue_title_update(payload))

    def test_returns_none_when_new_status_is_not_to_research(self):
        payload = {
            "triggerContext": {
                "trigger": "status_changed",
                "newStatus": "In Review",
                "id": "POI-4588",
                "title": "Methane closing warnings are merging",
            }
        }

        self.assertIsNone(build_issue_title_update(payload))

    def test_normalizes_status_casing_separators_and_camel_case(self):
        payload = {
            "triggerContext": {
                "trigger": "statusChanged",
                "newStatus": "to_research",
                "id": "POI-4588",
                "title": "Methane closing warnings are merging",
            }
        }

        self.assertEqual(
            build_issue_title_update(payload)["title"],
            "Cursor researching: Methane closing warnings are merging",
        )

    def test_skips_titles_that_already_have_research_prefix(self):
        payload = {
            "triggerContext": {
                "trigger": "status_changed",
                "newStatus": "to research",
                "id": "POI-4588",
                "title": "cursor researching: Methane closing warnings are merging",
            }
        }

        self.assertIsNone(build_issue_title_update(payload))

    def test_supports_nested_linear_update_payload_with_updated_fields(self):
        payload = {
            "action": "update",
            "type": "Issue",
            "updatedFields": ["state"],
            "data": {
                "identifier": "POI-4588",
                "title": "Methane closing warnings are merging",
                "state": {"name": "To Research"},
            },
        }

        self.assertEqual(
            build_issue_title_update(payload),
            {
                "action": "update_issue_title",
                "issueId": "POI-4588",
                "title": "Cursor researching: Methane closing warnings are merging",
            },
        )

    def test_supports_updated_from_state_id_payloads(self):
        payload = {
            "action": "update",
            "updatedFrom": {"stateId": "old-state-id"},
            "data": {
                "id": "linear-issue-id",
                "title": "Methane closing warnings are merging",
                "state": {"name": "To Research"},
            },
        }

        self.assertEqual(
            build_issue_title_update(payload)["issueId"],
            "linear-issue-id",
        )

    def test_prefers_explicit_new_status_over_existing_issue_status(self):
        payload = {
            "triggerContext": {
                "trigger": "status_changed",
                "newStatus": "To Research",
                "id": "POI-4588",
                "title": "Methane closing warnings are merging",
            },
            "data": {
                "state": {"name": "Backlog"},
            },
        }

        self.assertIsNotNone(build_issue_title_update(payload))

    def test_returns_none_without_issue_id(self):
        payload = {
            "triggerContext": {
                "trigger": "status_changed",
                "newStatus": "to research",
                "title": "Methane closing warnings are merging",
            }
        }

        self.assertIsNone(build_issue_title_update(payload))

    def test_returns_none_without_issue_title(self):
        payload = {
            "triggerContext": {
                "trigger": "status_changed",
                "newStatus": "to research",
                "id": "POI-4588",
            }
        }

        self.assertIsNone(build_issue_title_update(payload))

    def test_trims_issue_id_and_title(self):
        payload = {
            "triggerContext": {
                "trigger": "status_changed",
                "newStatus": "to research",
                "id": " POI-4588 ",
                "title": " Methane closing warnings are merging ",
            }
        }

        self.assertEqual(
            build_issue_title_update(payload),
            {
                "action": "update_issue_title",
                "issueId": "POI-4588",
                "title": "Cursor researching: Methane closing warnings are merging",
            },
        )

    def test_cli_prints_update_action_as_json(self):
        payload = {
            "triggerContext": {
                "trigger": "status_changed",
                "newStatus": "to research",
                "id": "POI-4588",
                "title": "Methane closing warnings are merging",
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
                "issueId": "POI-4588",
                "title": "Cursor researching: Methane closing warnings are merging",
            },
        )


if __name__ == "__main__":
    unittest.main()
