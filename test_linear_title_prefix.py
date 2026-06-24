import unittest

from linear_title_prefix import build_issue_title_update


class LinearTitlePrefixTest(unittest.TestCase):
    def test_cursor_trigger_context_status_change_to_research(self) -> None:
        payload = {
            "triggerContext": {
                "triggerType": "linear",
                "webhookType": "issue",
                "trigger": "status_changed",
                "newStatus": "To Research",
                "id": "POI-4455",
                "title": "Clean up ProductionSiteQualifiedOutputModule",
            }
        }

        self.assertEqual(
            build_issue_title_update(payload),
            {
                "action": "update_issue_title",
                "issueId": "POI-4455",
                "title": "Cursor researching: Clean up ProductionSiteQualifiedOutputModule",
            },
        )

    def test_automation_trigger_info_wrapper(self) -> None:
        payload = {
            "automation_trigger_info": {
                "triggerContext": {
                    "trigger": "status_changed",
                    "newStatus": "to research",
                    "id": "POI-4455",
                    "title": "Research this issue",
                }
            }
        }

        self.assertEqual(
            build_issue_title_update(payload),
            {
                "action": "update_issue_title",
                "issueId": "POI-4455",
                "title": "Cursor researching: Research this issue",
            },
        )

    def test_linear_webhook_state_update_to_research(self) -> None:
        payload = {
            "action": "update",
            "data": {
                "id": "issue-id",
                "title": "Investigate webhook payload",
                "state": {"name": "To Research"},
            },
            "updatedFrom": {"stateId": "old-state-id"},
        }

        self.assertEqual(
            build_issue_title_update(payload),
            {
                "action": "update_issue_title",
                "issueId": "issue-id",
                "title": "Cursor researching: Investigate webhook payload",
            },
        )

    def test_linear_webhook_status_update_to_research(self) -> None:
        payload = {
            "action": "update",
            "data": {
                "id": "issue-id",
                "title": "Investigate direct status",
                "status": "to-research",
            },
            "updatedFrom": {"status": "triage"},
        }

        self.assertEqual(
            build_issue_title_update(payload),
            {
                "action": "update_issue_title",
                "issueId": "issue-id",
                "title": "Cursor researching: Investigate direct status",
            },
        )

    def test_skips_non_research_status(self) -> None:
        payload = {
            "triggerContext": {
                "trigger": "status_changed",
                "newStatus": "Canceled",
                "id": "POI-4455",
                "title": "Clean up ProductionSiteQualifiedOutputModule",
            }
        }

        self.assertIsNone(build_issue_title_update(payload))

    def test_skips_non_status_change(self) -> None:
        payload = {
            "triggerContext": {
                "trigger": "comment_created",
                "newStatus": "To Research",
                "id": "POI-4455",
                "title": "Clean up ProductionSiteQualifiedOutputModule",
            }
        }

        self.assertIsNone(build_issue_title_update(payload))

    def test_skips_existing_prefix_case_insensitively(self) -> None:
        payload = {
            "triggerContext": {
                "trigger": "status_changed",
                "newStatus": "To Research",
                "id": "POI-4455",
                "title": "cursor researching: Already marked",
            }
        }

        self.assertIsNone(build_issue_title_update(payload))

    def test_skips_missing_title(self) -> None:
        payload = {
            "triggerContext": {
                "trigger": "status_changed",
                "newStatus": "To Research",
                "id": "POI-4455",
            }
        }

        self.assertIsNone(build_issue_title_update(payload))

    def test_skips_missing_issue_id(self) -> None:
        payload = {
            "triggerContext": {
                "trigger": "status_changed",
                "newStatus": "To Research",
                "title": "Missing issue id",
            }
        }

        self.assertIsNone(build_issue_title_update(payload))


if __name__ == "__main__":
    unittest.main()
