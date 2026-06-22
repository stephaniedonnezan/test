import unittest

from linear_title_prefix import build_issue_title_update


class BuildIssueTitleUpdateTest(unittest.TestCase):
    def test_builds_update_for_cursor_status_changed_payload(self):
        event = {
            "trigger": "status_changed",
            "newStatus": "To Research",
            "id": "POI-5093",
            "title": "MB export post QA updates",
        }

        self.assertEqual(
            build_issue_title_update(event),
            {
                "action": "update_issue_title",
                "issueId": "POI-5093",
                "title": "Cursor researching: MB export post QA updates",
            },
        )

    def test_supports_wrapped_automation_trigger_context(self):
        event = {
            "automationId": "automation-1",
            "automation_trigger_info": {
                "triggerContext": {
                    "triggerType": "linear",
                    "webhookType": "issue",
                    "trigger": "status_changed",
                    "newStatus": "to research",
                    "id": "POI-5093",
                    "title": "MB export post QA updates",
                }
            },
        }

        update = build_issue_title_update(event)

        self.assertIsNotNone(update)
        self.assertEqual(update["issueId"], "POI-5093")
        self.assertEqual(update["title"], "Cursor researching: MB export post QA updates")

    def test_ignores_status_changes_to_other_statuses(self):
        event = {
            "trigger": "status_changed",
            "newStatus": "Done",
            "id": "POI-5093",
            "title": "MB export post QA updates",
        }

        self.assertIsNone(build_issue_title_update(event))

    def test_ignores_non_status_change_triggers(self):
        event = {
            "trigger": "comment_created",
            "newStatus": "to research",
            "id": "POI-5093",
            "title": "MB export post QA updates",
        }

        self.assertIsNone(build_issue_title_update(event))

    def test_does_not_duplicate_existing_prefix(self):
        event = {
            "trigger": "status_changed",
            "newStatus": "to research",
            "id": "POI-5093",
            "title": "cursor researching: MB export post QA updates",
        }

        self.assertIsNone(build_issue_title_update(event))

    def test_normalizes_research_status_variants(self):
        for status in ("to_research", "to-research", "toResearch", " TO   RESEARCH "):
            with self.subTest(status=status):
                event = {
                    "trigger": "statusChanged",
                    "newStatus": status,
                    "id": "POI-5093",
                    "title": "MB export post QA updates",
                }

                self.assertEqual(
                    build_issue_title_update(event)["title"],
                    "Cursor researching: MB export post QA updates",
                )

    def test_falls_back_to_current_status_when_new_status_is_absent(self):
        event = {
            "trigger": "status_changed",
            "status": "To Research",
            "identifier": "POI-5093",
            "title": "MB export post QA updates",
        }

        update = build_issue_title_update(event)

        self.assertIsNotNone(update)
        self.assertEqual(update["issueId"], "POI-5093")

    def test_supports_nested_linear_issue_update_payload(self):
        event = {
            "action": "update",
            "updatedFields": ["state"],
            "data": {
                "id": "POI-5093",
                "title": "MB export post QA updates",
                "state": {"name": "To Research"},
            },
        }

        update = build_issue_title_update(event)

        self.assertIsNotNone(update)
        self.assertEqual(update["title"], "Cursor researching: MB export post QA updates")

    def test_supports_nested_issue_object(self):
        event = {
            "type": "Issue Updated",
            "updatedFields": [{"field": "workflowState"}],
            "data": {
                "issue": {
                    "identifier": "POI-5093",
                    "title": "MB export post QA updates",
                    "workflowState": {"name": "To Research"},
                }
            },
        }

        update = build_issue_title_update(event)

        self.assertIsNotNone(update)
        self.assertEqual(update["issueId"], "POI-5093")

    def test_ignores_generic_updates_without_status_field_changes(self):
        event = {
            "action": "update",
            "updatedFields": ["title"],
            "data": {
                "id": "POI-5093",
                "title": "MB export post QA updates",
                "state": {"name": "To Research"},
            },
        }

        self.assertIsNone(build_issue_title_update(event))

    def test_reads_target_status_from_changes_payload(self):
        event = {
            "action": "update",
            "changes": {"state": {"from": "Backlog", "to": {"name": "To Research"}}},
            "data": {
                "id": "POI-5093",
                "title": "MB export post QA updates",
                "state": {"name": "Backlog"},
            },
        }

        update = build_issue_title_update(event)

        self.assertIsNotNone(update)
        self.assertEqual(update["title"], "Cursor researching: MB export post QA updates")

    def test_requires_issue_id_and_title(self):
        self.assertIsNone(
            build_issue_title_update(
                {
                    "trigger": "status_changed",
                    "newStatus": "to research",
                    "title": "MB export post QA updates",
                }
            )
        )
        self.assertIsNone(
            build_issue_title_update(
                {
                    "trigger": "status_changed",
                    "newStatus": "to research",
                    "id": "POI-5093",
                }
            )
        )


if __name__ == "__main__":
    unittest.main()
