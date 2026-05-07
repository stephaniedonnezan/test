import unittest

from linear_title_prefix import build_issue_title_update


class BuildIssueTitleUpdateTest(unittest.TestCase):
    def test_prefixes_title_for_nested_status_change_to_research(self):
        event = {
            "triggerContext": {
                "trigger": "status_changed",
                "newStatus": "To Research",
                "id": "POI-3763",
                "title": "Update the traceability deliveries download file template",
            }
        }

        self.assertEqual(
            build_issue_title_update(event),
            {
                "action": "update_issue_title",
                "issueId": "POI-3763",
                "title": (
                    "Cursor researching: "
                    "Update the traceability deliveries download file template"
                ),
            },
        )

    def test_accepts_linear_data_issue_payload(self):
        event = {
            "action": "statusChanged",
            "data": {
                "issue": {
                    "identifier": "POI-123",
                    "title": "Review extracted document fields",
                    "state": {"name": "to_research"},
                }
            },
        }

        self.assertEqual(
            build_issue_title_update(event),
            {
                "action": "update_issue_title",
                "issueId": "POI-123",
                "title": "Cursor researching: Review extracted document fields",
            },
        )

    def test_accepts_top_level_issue_with_top_level_status(self):
        event = {
            "webhookType": "status_changed",
            "issue": {
                "id": "POI-124",
                "title": "Top-level issue payload",
            },
            "status": "to research",
        }

        self.assertEqual(
            build_issue_title_update(event),
            {
                "action": "update_issue_title",
                "issueId": "POI-124",
                "title": "Cursor researching: Top-level issue payload",
            },
        )

    def test_accepts_updated_issue_when_status_field_changed(self):
        event = {
            "type": "Issue Updated",
            "updatedFields": ["description", "state"],
            "status": "to-research",
            "issueId": "POI-125",
            "title": "Research a biomethane parser",
        }

        self.assertEqual(
            build_issue_title_update(event)["title"],
            "Cursor researching: Research a biomethane parser",
        )

    def test_accepts_action_status_changed_when_webhook_type_is_issue(self):
        event = {
            "webhookType": "issue",
            "action": "statusChanged",
            "newStatus": "to research",
            "issueId": "POI-126",
            "title": "Investigate carbon KPI",
        }

        self.assertEqual(
            build_issue_title_update(event)["title"],
            "Cursor researching: Investigate carbon KPI",
        )

    def test_skips_non_status_change_trigger(self):
        event = {
            "triggerContext": {
                "trigger": "comment_created",
                "newStatus": "to research",
                "id": "POI-3763",
                "title": "Update the traceability deliveries download file template",
            }
        }

        self.assertIsNone(build_issue_title_update(event))

    def test_skips_status_change_to_other_status(self):
        event = {
            "triggerContext": {
                "trigger": "status_changed",
                "newStatus": "Done",
                "id": "POI-3763",
                "title": "Update the traceability deliveries download file template",
            }
        }

        self.assertIsNone(build_issue_title_update(event))

    def test_skips_existing_prefix_case_insensitively(self):
        event = {
            "trigger": "status_changed",
            "new_status": "TO RESEARCH",
            "id": "POI-3763",
            "title": "cursor researching: Existing prefix",
        }

        self.assertIsNone(build_issue_title_update(event))

    def test_trims_title_before_prefixing(self):
        event = {
            "trigger": "status_changed",
            "newStatus": "toResearch",
            "id": "POI-3763",
            "title": "  Update the template  ",
        }

        self.assertEqual(
            build_issue_title_update(event)["title"],
            "Cursor researching: Update the template",
        )

    def test_skips_missing_issue_id_or_title(self):
        self.assertIsNone(
            build_issue_title_update(
                {
                    "trigger": "status_changed",
                    "newStatus": "to research",
                    "title": "Update the template",
                }
            )
        )
        self.assertIsNone(
            build_issue_title_update(
                {
                    "trigger": "status_changed",
                    "newStatus": "to research",
                    "id": "POI-3763",
                }
            )
        )

    def test_skips_non_mapping_payload(self):
        self.assertIsNone(build_issue_title_update(None))


if __name__ == "__main__":
    unittest.main()
