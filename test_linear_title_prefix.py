import unittest

from linear_title_prefix import build_issue_title_update


class BuildIssueTitleUpdateTest(unittest.TestCase):
    def test_prefixes_title_for_to_research_status_change(self):
        result = build_issue_title_update(
            {
                "triggerContext": {
                    "trigger": "status_changed",
                    "newStatus": "To Research",
                    "id": "POI-3957",
                    "title": "Fragile CO2 qualified inputs",
                }
            }
        )

        self.assertEqual(
            result,
            {
                "action": "update_issue_title",
                "issueId": "POI-3957",
                "title": "Cursor researching: Fragile CO2 qualified inputs",
            },
        )

    def test_ignores_other_statuses(self):
        result = build_issue_title_update(
            {
                "triggerContext": {
                    "trigger": "status_changed",
                    "newStatus": "Canceled",
                    "id": "POI-3957",
                    "title": "Fragile CO2 qualified inputs",
                }
            }
        )

        self.assertIsNone(result)

    def test_ignores_non_status_change_events(self):
        result = build_issue_title_update(
            {
                "triggerContext": {
                    "trigger": "comment_created",
                    "newStatus": "To Research",
                    "id": "POI-3957",
                    "title": "Fragile CO2 qualified inputs",
                }
            }
        )

        self.assertIsNone(result)

    def test_does_not_duplicate_existing_prefix(self):
        result = build_issue_title_update(
            {
                "triggerContext": {
                    "trigger": "statusChanged",
                    "newStatus": "to_research",
                    "id": "POI-3957",
                    "title": "cursor researching: Fragile CO2 qualified inputs",
                }
            }
        )

        self.assertIsNone(result)

    def test_accepts_kebab_case_status(self):
        result = build_issue_title_update(
            {
                "triggerContext": {
                    "trigger": "statusChanged",
                    "newStatus": "to-research",
                    "id": "POI-3957",
                    "title": "Fragile CO2 qualified inputs",
                }
            }
        )

        self.assertEqual(result["title"], "Cursor researching: Fragile CO2 qualified inputs")

    def test_accepts_camel_case_status(self):
        result = build_issue_title_update(
            {
                "triggerContext": {
                    "trigger": "statusChanged",
                    "newStatus": "toResearch",
                    "id": "POI-3957",
                    "title": "Fragile CO2 qualified inputs",
                }
            }
        )

        self.assertEqual(result["title"], "Cursor researching: Fragile CO2 qualified inputs")

    def test_falls_back_to_status_field(self):
        result = build_issue_title_update(
            {
                "triggerContext": {
                    "trigger": "status_changed",
                    "status": "To Research",
                    "issueId": "POI-3957",
                    "title": "Fragile CO2 qualified inputs",
                }
            }
        )

        self.assertEqual(result["issueId"], "POI-3957")

    def test_falls_back_to_state_name(self):
        result = build_issue_title_update(
            {
                "action": "statusChanged",
                "data": {
                    "issue": {
                        "identifier": "POI-3957",
                        "title": "Fragile CO2 qualified inputs",
                        "state": {"name": "To Research"},
                    }
                },
            }
        )

        self.assertEqual(result["issueId"], "POI-3957")

    def test_issue_updated_must_include_status_field_change(self):
        result = build_issue_title_update(
            {
                "type": "Issue Updated",
                "updatedFields": ["status"],
                "issue": {
                    "id": "POI-3957",
                    "title": "Fragile CO2 qualified inputs",
                    "state": {"name": "To Research"},
                },
            }
        )

        self.assertEqual(result["title"], "Cursor researching: Fragile CO2 qualified inputs")

    def test_issue_updated_ignores_unrelated_field_changes(self):
        result = build_issue_title_update(
            {
                "type": "Issue Updated",
                "updatedFields": ["description"],
                "issue": {
                    "id": "POI-3957",
                    "title": "Fragile CO2 qualified inputs",
                    "state": {"name": "To Research"},
                },
            }
        )

        self.assertIsNone(result)

    def test_requires_issue_id(self):
        result = build_issue_title_update(
            {
                "triggerContext": {
                    "trigger": "status_changed",
                    "newStatus": "To Research",
                    "title": "Fragile CO2 qualified inputs",
                }
            }
        )

        self.assertIsNone(result)

    def test_requires_issue_title(self):
        result = build_issue_title_update(
            {
                "triggerContext": {
                    "trigger": "status_changed",
                    "newStatus": "To Research",
                    "id": "POI-3957",
                }
            }
        )

        self.assertIsNone(result)

    def test_rejects_non_mapping_payload(self):
        self.assertIsNone(build_issue_title_update(None))

    def test_trims_title_and_issue_id(self):
        result = build_issue_title_update(
            {
                "triggerContext": {
                    "trigger": "status_changed",
                    "newStatus": "To Research",
                    "id": "  POI-3957  ",
                    "title": "  Fragile CO2 qualified inputs  ",
                }
            }
        )

        self.assertEqual(
            result,
            {
                "action": "update_issue_title",
                "issueId": "POI-3957",
                "title": "Cursor researching: Fragile CO2 qualified inputs",
            },
        )


if __name__ == "__main__":
    unittest.main()
