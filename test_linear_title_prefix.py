import json
import subprocess
import sys
import unittest

from linear_title_prefix import build_issue_title_update


class BuildIssueTitleUpdateTest(unittest.TestCase):
    def test_prefixes_title_for_cloud_status_change_to_research(self):
        event = {
            "automation_trigger_info": {
                "triggerContext": {
                    "trigger": "status_changed",
                    "newStatus": "To Research",
                    "id": "POI-4047",
                    "title": "[Date picker in Automate] choose year and month faster",
                }
            }
        }

        self.assertEqual(
            build_issue_title_update(event),
            {
                "action": "update_issue_title",
                "issueId": "POI-4047",
                "title": (
                    "Cursor researching: "
                    "[Date picker in Automate] choose year and month faster"
                ),
            },
        )

    def test_skips_cloud_status_change_to_non_research_status(self):
        event = {
            "automation_trigger_info": {
                "triggerContext": {
                    "trigger": "status_changed",
                    "newStatus": "QA UX/UI",
                    "id": "POI-4047",
                    "title": "[Date picker in Automate] choose year and month faster",
                }
            }
        }

        self.assertIsNone(build_issue_title_update(event))

    def test_accepts_flat_trigger_context_payload(self):
        event = {
            "triggerContext": {
                "webhookType": "statusChanged",
                "new_status": "to_research",
                "issueId": "POI-123",
                "title": "Review extracted document fields",
            }
        }

        self.assertEqual(
            build_issue_title_update(event)["title"],
            "Cursor researching: Review extracted document fields",
        )

    def test_accepts_linear_data_issue_payload(self):
        event = {
            "action": "statusChanged",
            "data": {
                "issue": {
                    "identifier": "POI-124",
                    "title": "Research a biomethane parser",
                    "state": {"name": "to-research"},
                }
            },
        }

        self.assertEqual(
            build_issue_title_update(event),
            {
                "action": "update_issue_title",
                "issueId": "POI-124",
                "title": "Cursor researching: Research a biomethane parser",
            },
        )

    def test_accepts_updated_issue_when_workflow_state_field_changed(self):
        event = {
            "type": "Issue Updated",
            "updatedFields": ["description", "workflowState"],
            "newWorkflowState": "toResearch",
            "key": "POI-125",
            "title": "Investigate supplier mappings",
        }

        self.assertEqual(
            build_issue_title_update(event)["title"],
            "Cursor researching: Investigate supplier mappings",
        )

    def test_accepts_status_from_changes_payload(self):
        event = {
            "action": "update",
            "data": {
                "issue": {
                    "identifier": "POI-126",
                    "title": "Research parser retry behavior",
                }
            },
            "changes": {
                "state": {
                    "from": {"name": "Todo"},
                    "to": {"name": "to research"},
                }
            },
        }

        self.assertEqual(
            build_issue_title_update(event)["issueId"],
            "POI-126",
        )

    def test_skips_issue_update_when_status_field_did_not_change(self):
        event = {
            "action": "update",
            "updatedFields": ["description"],
            "status": "to research",
            "id": "POI-127",
            "title": "Research parser retry behavior",
        }

        self.assertIsNone(build_issue_title_update(event))

    def test_skips_non_status_change_trigger(self):
        event = {
            "trigger": "comment_created",
            "newStatus": "to research",
            "id": "POI-128",
            "title": "Research parser retry behavior",
        }

        self.assertIsNone(build_issue_title_update(event))

    def test_skips_status_change_to_other_status(self):
        event = {
            "trigger": "status_changed",
            "newStatus": "Done",
            "id": "POI-129",
            "title": "Research parser retry behavior",
        }

        self.assertIsNone(build_issue_title_update(event))

    def test_skips_existing_prefix_case_insensitively(self):
        event = {
            "trigger": "status_changed",
            "newStatus": "TO RESEARCH",
            "id": "POI-130",
            "title": "cursor researching: Research parser retry behavior",
        }

        self.assertIsNone(build_issue_title_update(event))

    def test_trims_issue_id_and_title_before_prefixing(self):
        event = {
            "trigger": "status_changed",
            "newStatus": "to research",
            "id": "  POI-131  ",
            "title": "  Research parser retry behavior  ",
        }

        self.assertEqual(
            build_issue_title_update(event),
            {
                "action": "update_issue_title",
                "issueId": "POI-131",
                "title": "Cursor researching: Research parser retry behavior",
            },
        )

    def test_skips_missing_issue_id_or_title_and_non_mapping_payload(self):
        self.assertIsNone(
            build_issue_title_update(
                {
                    "trigger": "status_changed",
                    "newStatus": "to research",
                    "title": "Research parser retry behavior",
                }
            )
        )
        self.assertIsNone(
            build_issue_title_update(
                {
                    "trigger": "status_changed",
                    "newStatus": "to research",
                    "id": "POI-132",
                }
            )
        )
        self.assertIsNone(build_issue_title_update(None))

    def test_cli_outputs_update_action_as_json(self):
        event = {
            "trigger": "status_changed",
            "newStatus": "to research",
            "id": "POI-133",
            "title": "Research parser retry behavior",
        }

        process = subprocess.run(
            [sys.executable, "linear_title_prefix.py"],
            check=True,
            input=json.dumps(event),
            text=True,
            capture_output=True,
        )

        self.assertEqual(
            json.loads(process.stdout),
            {
                "action": "update_issue_title",
                "issueId": "POI-133",
                "title": "Cursor researching: Research parser retry behavior",
            },
        )


if __name__ == "__main__":
    unittest.main()
