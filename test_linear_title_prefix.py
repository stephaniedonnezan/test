import json
import subprocess
import sys
import unittest

from linear_title_prefix import build_issue_title_update


class BuildIssueTitleUpdateTests(unittest.TestCase):
    def test_prefixes_flat_trigger_context_status_change(self):
        event = {
            "triggerContext": {
                "trigger": "status_changed",
                "newStatus": "To Research",
                "id": "POI-4776",
                "title": "LHV plan 7-9",
            }
        }

        self.assertEqual(
            build_issue_title_update(event),
            {
                "action": "update_issue_title",
                "issueId": "POI-4776",
                "title": "Cursor researching: LHV plan 7-9",
            },
        )

    def test_accepts_top_level_status_change_payload(self):
        event = {
            "trigger": "statusChanged",
            "status": "to-research",
            "issueId": "POI-123",
            "title": "Investigate electrolyzer data",
        }

        self.assertEqual(
            build_issue_title_update(event),
            {
                "action": "update_issue_title",
                "issueId": "POI-123",
                "title": "Cursor researching: Investigate electrolyzer data",
            },
        )

    def test_accepts_camel_case_target_status(self):
        event = {
            "trigger": "status_changed",
            "newStatus": "toResearch",
            "identifier": "POI-124",
            "title": "Research hydrogen storage",
        }

        self.assertEqual(
            build_issue_title_update(event)["title"],
            "Cursor researching: Research hydrogen storage",
        )

    def test_ignores_other_statuses(self):
        event = {
            "trigger": "status_changed",
            "newStatus": "Todo",
            "id": "POI-4776",
            "title": "LHV plan 7-9",
        }

        self.assertIsNone(build_issue_title_update(event))

    def test_ignores_non_status_change_trigger(self):
        event = {
            "trigger": "label_changed",
            "newStatus": "To Research",
            "id": "POI-4776",
            "title": "LHV plan 7-9",
        }

        self.assertIsNone(build_issue_title_update(event))

    def test_skips_titles_that_already_have_prefix(self):
        event = {
            "trigger": "status_changed",
            "newStatus": "to research",
            "id": "POI-4776",
            "title": "cursor researching: LHV plan 7-9",
        }

        self.assertIsNone(build_issue_title_update(event))

    def test_accepts_nested_linear_issue_update_with_state_change(self):
        event = {
            "action": "update",
            "type": "Issue",
            "data": {
                "id": "linear-issue-id",
                "identifier": "POI-125",
                "title": "Map methane routes",
                "state": {"name": "To Research"},
            },
            "updatedFrom": {"stateId": "previous-state-id"},
        }

        self.assertEqual(
            build_issue_title_update(event),
            {
                "action": "update_issue_title",
                "issueId": "POI-125",
                "title": "Cursor researching: Map methane routes",
            },
        )

    def test_accepts_nested_issue_payload_from_data_issue(self):
        event = {
            "webhookType": "status_changed",
            "new_status": "to_research",
            "data": {
                "issue": {
                    "issue_id": "POI-126",
                    "title": "Review carbon model",
                }
            },
        }

        self.assertEqual(
            build_issue_title_update(event)["issueId"],
            "POI-126",
        )

    def test_ignores_generic_issue_update_without_status_change(self):
        event = {
            "action": "update",
            "type": "Issue",
            "data": {
                "identifier": "POI-127",
                "title": "Map methane routes",
                "state": {"name": "To Research"},
            },
            "updatedFields": ["description"],
        }

        self.assertIsNone(build_issue_title_update(event))

    def test_requires_issue_id_and_title(self):
        event = {
            "trigger": "status_changed",
            "newStatus": "to research",
            "title": "Missing issue id",
        }

        self.assertIsNone(build_issue_title_update(event))

    def test_trims_issue_id_and_title(self):
        event = {
            "trigger": "status_changed",
            "newStatus": "to research",
            "issueId": " POI-128 ",
            "title": "  Confirm LHV assumptions  ",
        }

        self.assertEqual(
            build_issue_title_update(event),
            {
                "action": "update_issue_title",
                "issueId": "POI-128",
                "title": "Cursor researching: Confirm LHV assumptions",
            },
        )


class CliTests(unittest.TestCase):
    def test_cli_prints_update_action_for_matching_payload(self):
        payload = {
            "trigger": "status_changed",
            "newStatus": "to research",
            "id": "POI-129",
            "title": "Prepare feedstock review",
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
                "issueId": "POI-129",
                "title": "Cursor researching: Prepare feedstock review",
            },
        )


if __name__ == "__main__":
    unittest.main()
