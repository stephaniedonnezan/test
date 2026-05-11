import unittest

from linear_title_prefix import build_issue_title_update


class BuildIssueTitleUpdateTest(unittest.TestCase):
    def test_prefixes_title_for_status_changed_to_research(self):
        update = build_issue_title_update(
            {
                "triggerContext": {
                    "trigger": "status_changed",
                    "newStatus": "to research",
                    "id": "POI-4198",
                    "title": "Allow UBA POS creation for methane",
                }
            }
        )

        self.assertEqual(
            update,
            {
                "action": "update_issue_title",
                "issueId": "POI-4198",
                "title": "Cursor researching: Allow UBA POS creation for methane",
            },
        )

    def test_ignores_other_statuses(self):
        update = build_issue_title_update(
            {
                "triggerContext": {
                    "trigger": "status_changed",
                    "newStatus": "QA",
                    "id": "POI-4198",
                    "title": "Allow UBA POS creation for methane",
                }
            }
        )

        self.assertIsNone(update)

    def test_ignores_non_status_change_triggers(self):
        update = build_issue_title_update(
            {
                "triggerContext": {
                    "trigger": "comment_created",
                    "newStatus": "to research",
                    "id": "POI-4198",
                    "title": "Allow UBA POS creation for methane",
                }
            }
        )

        self.assertIsNone(update)

    def test_does_not_duplicate_existing_prefix(self):
        update = build_issue_title_update(
            {
                "triggerContext": {
                    "trigger": "statusChanged",
                    "newStatus": "To Research",
                    "id": "POI-4198",
                    "title": "cursor researching: Allow UBA POS creation for methane",
                }
            }
        )

        self.assertIsNone(update)

    def test_accepts_common_status_spellings(self):
        update = build_issue_title_update(
            {
                "trigger": "status-changed",
                "new_status": "ToResearch",
                "issueId": "POI-4198",
                "title": "Allow UBA POS creation for methane",
            }
        )

        self.assertEqual(update["title"], "Cursor researching: Allow UBA POS creation for methane")

    def test_falls_back_to_nested_state_name(self):
        update = build_issue_title_update(
            {
                "action": "updated",
                "updatedFields": ["stateId"],
                "data": {
                    "id": "issue-uuid",
                    "identifier": "POI-4198",
                    "title": "Allow UBA POS creation for methane",
                    "state": {"name": "To Research"},
                },
            }
        )

        self.assertEqual(update["issueId"], "POI-4198")

    def test_reads_nested_issue_payload(self):
        update = build_issue_title_update(
            {
                "type": "Issue",
                "updatedFields": ["workflowState"],
                "data": {
                    "issue": {
                        "issueId": "POI-4198",
                        "title": "Allow UBA POS creation for methane",
                        "workflowState": {"name": "to_research"},
                    }
                },
            }
        )

        self.assertEqual(update["issueId"], "POI-4198")
        self.assertEqual(update["title"], "Cursor researching: Allow UBA POS creation for methane")

    def test_prefers_nested_issue_id_over_top_level_webhook_id(self):
        update = build_issue_title_update(
            {
                "id": "webhook-event-id",
                "trigger": "status_changed",
                "newStatus": "to research",
                "data": {
                    "id": "issue-uuid",
                    "identifier": "POI-4198",
                    "title": "Allow UBA POS creation for methane",
                },
            }
        )

        self.assertEqual(update["issueId"], "POI-4198")

    def test_requires_issue_id_and_title(self):
        update = build_issue_title_update(
            {
                "trigger": "status_changed",
                "newStatus": "to research",
                "id": "POI-4198",
            }
        )

        self.assertIsNone(update)

    def test_ignores_non_mapping_payloads(self):
        self.assertIsNone(build_issue_title_update(None))


if __name__ == "__main__":
    unittest.main()
