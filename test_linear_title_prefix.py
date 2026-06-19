import unittest

from linear_title_prefix import build_issue_title_update, normalize_status


class LinearTitlePrefixTest(unittest.TestCase):
    def test_prefixes_cursor_trigger_context_when_status_moves_to_research(self):
        event = {
            "triggerContext": {
                "triggerType": "status_changed",
                "webhookType": "issue",
                "newStatus": "To Research",
                "id": "POI-5039",
                "title": "Hide default emissions section",
            }
        }

        self.assertEqual(
            build_issue_title_update(event),
            {
                "action": "update_issue_title",
                "issueId": "POI-5039",
                "title": "Cursor researching: Hide default emissions section",
            },
        )

    def test_prefixes_nested_automation_trigger_info(self):
        event = {
            "automation_trigger_info": {
                "triggerContext": {
                    "trigger": "status_changed",
                    "webhookType": "issue",
                    "newStatus": "to_research",
                    "issueId": "POI-1",
                    "title": "Investigate automation",
                }
            }
        }

        update = build_issue_title_update(event)

        self.assertIsNotNone(update)
        self.assertEqual(update["title"], "Cursor researching: Investigate automation")

    def test_normalizes_camel_case_status(self):
        event = {
            "triggerContext": {
                "trigger": "status_changed",
                "webhookType": "issue",
                "newStatus": "toResearch",
                "id": "POI-2",
                "title": "Camel case status",
            }
        }

        self.assertEqual(
            build_issue_title_update(event)["title"],
            "Cursor researching: Camel case status",
        )

    def test_uses_current_linear_issue_state_when_state_id_changed(self):
        event = {
            "type": "Issue",
            "action": "update",
            "data": {
                "issue": {
                    "id": "linear-issue-id",
                    "title": "Linear webhook payload",
                    "state": {"name": "To Research"},
                }
            },
            "updatedFrom": {"stateId": "old-state-id"},
        }

        self.assertEqual(
            build_issue_title_update(event),
            {
                "action": "update_issue_title",
                "issueId": "linear-issue-id",
                "title": "Cursor researching: Linear webhook payload",
            },
        )

    def test_uses_changed_status_to_value(self):
        event = {
            "issue": {"identifier": "POI-3", "title": "Changed field payload"},
            "changes": {"status": {"from": "Backlog", "to": "To Research"}},
        }

        self.assertEqual(
            build_issue_title_update(event)["title"],
            "Cursor researching: Changed field payload",
        )

    def test_skips_non_research_status(self):
        event = {
            "triggerContext": {
                "triggerType": "status_changed",
                "webhookType": "issue",
                "newStatus": "Agent research to review",
                "id": "POI-5039",
                "title": "Hide default emissions section",
            }
        }

        self.assertIsNone(build_issue_title_update(event))

    def test_skips_when_already_prefixed(self):
        event = {
            "triggerContext": {
                "triggerType": "status_changed",
                "webhookType": "issue",
                "newStatus": "To Research",
                "id": "POI-4",
                "title": "cursor researching: Already handled",
            }
        }

        self.assertIsNone(build_issue_title_update(event))

    def test_skips_when_required_issue_fields_are_missing(self):
        event = {
            "triggerContext": {
                "triggerType": "status_changed",
                "webhookType": "issue",
                "newStatus": "To Research",
                "id": "POI-5",
            }
        }

        self.assertIsNone(build_issue_title_update(event))

    def test_ignores_current_status_without_status_change_evidence(self):
        event = {
            "webhookType": "issue",
            "status": "To Research",
            "id": "POI-6",
            "title": "No change event",
        }

        self.assertIsNone(build_issue_title_update(event))

    def test_status_normalization(self):
        self.assertEqual(normalize_status("to-research"), "to research")
        self.assertEqual(normalize_status("ToResearch"), "to research")
        self.assertEqual(normalize_status({"name": "TO_RESEARCH"}), "to research")


if __name__ == "__main__":
    unittest.main()
