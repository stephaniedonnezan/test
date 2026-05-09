import unittest

from linear_title_prefix import build_issue_title_update


class BuildIssueTitleUpdateTest(unittest.TestCase):
    def test_prefixes_title_for_status_changed_to_research(self):
        event = {
            "triggerContext": {
                "trigger": "status_changed",
                "newStatus": "to research",
                "id": "POI-3672",
                "title": "CI KPIs on the site management page are wrong",
            }
        }

        self.assertEqual(
            build_issue_title_update(event),
            {
                "action": "update_issue_title",
                "issueId": "POI-3672",
                "title": "Cursor researching: CI KPIs on the site management page are wrong",
            },
        )

    def test_ignores_other_statuses(self):
        event = {
            "triggerContext": {
                "trigger": "status_changed",
                "newStatus": "In Review",
                "id": "POI-3672",
                "title": "CI KPIs on the site management page are wrong",
            }
        }

        self.assertIsNone(build_issue_title_update(event))

    def test_ignores_non_status_change_triggers(self):
        event = {
            "triggerContext": {
                "trigger": "comment_created",
                "newStatus": "to research",
                "id": "POI-3672",
                "title": "CI KPIs on the site management page are wrong",
            }
        }

        self.assertIsNone(build_issue_title_update(event))

    def test_does_not_duplicate_existing_prefix(self):
        event = {
            "trigger": "status_changed",
            "newStatus": "to research",
            "id": "POI-3672",
            "title": "cursor researching: CI KPIs on the site management page are wrong",
        }

        self.assertIsNone(build_issue_title_update(event))

    def test_normalizes_status_and_trigger_variants(self):
        event = {
            "trigger": "statusChanged",
            "new_status": "To-Research",
            "issueId": "POI-3672",
            "title": "CI KPIs on the site management page are wrong",
        }

        self.assertEqual(
            build_issue_title_update(event),
            {
                "action": "update_issue_title",
                "issueId": "POI-3672",
                "title": "Cursor researching: CI KPIs on the site management page are wrong",
            },
        )

    def test_accepts_linear_issue_updated_when_status_field_changed(self):
        event = {
            "type": "Issue Updated",
            "updatedFields": ["description", "state"],
            "state": {"name": "To Research"},
            "data": {
                "issue": {
                    "id": "POI-3672",
                    "title": "CI KPIs on the site management page are wrong",
                }
            },
        }

        self.assertEqual(
            build_issue_title_update(event),
            {
                "action": "update_issue_title",
                "issueId": "POI-3672",
                "title": "Cursor researching: CI KPIs on the site management page are wrong",
            },
        )

    def test_accepts_trigger_context_nested_issue_payload(self):
        event = {
            "triggerContext": {
                "trigger": "status_changed",
                "status": "to research",
                "data": {
                    "issue": {
                        "identifier": "POI-3672",
                        "title": "CI KPIs on the site management page are wrong",
                    }
                },
            }
        }

        self.assertEqual(
            build_issue_title_update(event),
            {
                "action": "update_issue_title",
                "issueId": "POI-3672",
                "title": "Cursor researching: CI KPIs on the site management page are wrong",
            },
        )

    def test_trims_title_and_issue_id(self):
        event = {
            "trigger": "status_changed",
            "newStatus": "to research",
            "id": " POI-3672 ",
            "title": " CI KPIs on the site management page are wrong ",
        }

        self.assertEqual(
            build_issue_title_update(event),
            {
                "action": "update_issue_title",
                "issueId": "POI-3672",
                "title": "Cursor researching: CI KPIs on the site management page are wrong",
            },
        )

    def test_requires_title(self):
        event = {
            "trigger": "status_changed",
            "newStatus": "to research",
            "id": "POI-3672",
            "title": " ",
        }

        self.assertIsNone(build_issue_title_update(event))

    def test_requires_issue_id(self):
        event = {
            "trigger": "status_changed",
            "newStatus": "to research",
            "title": "CI KPIs on the site management page are wrong",
        }

        self.assertIsNone(build_issue_title_update(event))

    def test_ignores_non_mapping_payloads(self):
        self.assertIsNone(build_issue_title_update(None))


if __name__ == "__main__":
    unittest.main()
