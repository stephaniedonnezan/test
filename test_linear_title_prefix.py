import json
import subprocess
import sys
import unittest

from linear_title_prefix import build_issue_title_update, handle_issue_status_changed


class LinearTitlePrefixTest(unittest.TestCase):
    def test_builds_title_update_for_flat_status_changed_payload(self):
        event = {
            "trigger": "status_changed",
            "newStatus": "To Research",
            "id": "POI-4581",
            "title": "DPP of h2 crashing when you try to load it",
        }

        self.assertEqual(
            build_issue_title_update(event),
            {
                "action": "update_issue_title",
                "issueId": "POI-4581",
                "title": "Cursor researching: DPP of h2 crashing when you try to load it",
            },
        )

    def test_accepts_automation_trigger_context_wrapper(self):
        event = {
            "triggerContext": {
                "trigger": "status_changed",
                "newStatus": "To Research",
                "id": "POI-4581",
                "title": "DPP of h2 crashing when you try to load it",
            }
        }

        self.assertEqual(
            build_issue_title_update(event),
            {
                "action": "update_issue_title",
                "issueId": "POI-4581",
                "title": "Cursor researching: DPP of h2 crashing when you try to load it",
            },
        )

    def test_accepts_case_and_separator_variants(self):
        event = {
            "trigger": "statusChanged",
            "new_status": "to_research",
            "issueId": "POI-4581",
            "title": "Hydrogen PLS DPP crash",
        }

        self.assertEqual(
            build_issue_title_update(event)["title"],
            "Cursor researching: Hydrogen PLS DPP crash",
        )

    def test_ignores_non_research_status(self):
        event = {
            "trigger": "status_changed",
            "newStatus": "In Progress",
            "id": "POI-4581",
            "title": "Hydrogen PLS DPP crash",
        }

        self.assertIsNone(build_issue_title_update(event))

    def test_ignores_non_status_change_trigger(self):
        event = {
            "trigger": "comment_created",
            "newStatus": "To Research",
            "id": "POI-4581",
            "title": "Hydrogen PLS DPP crash",
        }

        self.assertIsNone(build_issue_title_update(event))

    def test_does_not_duplicate_existing_prefix(self):
        event = {
            "trigger": "status_changed",
            "newStatus": "To Research",
            "id": "POI-4581",
            "title": "cursor researching: Hydrogen PLS DPP crash",
        }

        self.assertIsNone(build_issue_title_update(event))

    def test_accepts_nested_linear_issue_update_when_state_changed(self):
        event = {
            "action": "update",
            "type": "Issue",
            "updatedFields": ["state"],
            "data": {
                "identifier": "POI-4581",
                "title": "Hydrogen PLS DPP crash",
                "state": {"name": "To Research"},
            },
        }

        self.assertEqual(
            build_issue_title_update(event),
            {
                "action": "update_issue_title",
                "issueId": "POI-4581",
                "title": "Cursor researching: Hydrogen PLS DPP crash",
            },
        )

    def test_ignores_nested_linear_issue_update_without_state_change(self):
        event = {
            "action": "update",
            "type": "Issue",
            "updatedFields": ["description"],
            "data": {
                "identifier": "POI-4581",
                "title": "Hydrogen PLS DPP crash",
                "state": {"name": "To Research"},
            },
        }

        self.assertIsNone(build_issue_title_update(event))

    def test_wrapper_uses_same_behavior(self):
        event = {
            "trigger": "status_changed",
            "newStatus": "To Research",
            "id": "POI-4581",
            "title": "Hydrogen PLS DPP crash",
        }

        self.assertEqual(handle_issue_status_changed(event), build_issue_title_update(event))

    def test_cli_prints_update_action(self):
        event = {
            "trigger": "status_changed",
            "newStatus": "To Research",
            "id": "POI-4581",
            "title": "Hydrogen PLS DPP crash",
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
                "issueId": "POI-4581",
                "title": "Cursor researching: Hydrogen PLS DPP crash",
            },
        )


if __name__ == "__main__":
    unittest.main()
