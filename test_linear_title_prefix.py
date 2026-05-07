import unittest

from linear_title_prefix import build_issue_title_update


class BuildIssueTitleUpdateTest(unittest.TestCase):
    def test_returns_title_update_for_to_research_status_change(self):
        event = {
            "trigger": "status_changed",
            "newStatus": "to research",
            "id": "POI-3672",
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

    def test_reads_automation_trigger_context_payload(self):
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

    def test_accepts_linear_data_issue_shape(self):
        event = {
            "action": "statusChanged",
            "data": {
                "issue": {
                    "identifier": "POI-3672",
                    "title": "CI KPIs on the site management page are wrong",
                    "state": {"name": "To Research"},
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

    def test_accepts_status_separator_and_case_variants(self):
        event = {
            "trigger": "statusChanged",
            "new_status": "To_Research",
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

    def test_accepts_issue_updated_when_status_was_updated(self):
        event = {
            "type": "Issue Updated",
            "updatedFields": ["title", "status"],
            "status": "To Research",
            "id": "POI-3672",
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

    def test_ignores_issue_updated_when_status_was_not_updated(self):
        event = {
            "type": "Issue Updated",
            "updatedFields": ["title"],
            "status": "To Research",
            "id": "POI-3672",
            "title": "CI KPIs on the site management page are wrong",
        }

        self.assertIsNone(build_issue_title_update(event))

    def test_ignores_other_statuses(self):
        event = {
            "trigger": "status_changed",
            "newStatus": "In Progress",
            "id": "POI-3672",
            "title": "CI KPIs on the site management page are wrong",
        }

        self.assertIsNone(build_issue_title_update(event))

    def test_ignores_other_triggers(self):
        event = {
            "trigger": "comment_created",
            "newStatus": "to research",
            "id": "POI-3672",
            "title": "CI KPIs on the site management page are wrong",
        }

        self.assertIsNone(build_issue_title_update(event))

    def test_ignores_already_prefixed_titles_case_insensitively(self):
        event = {
            "trigger": "status_changed",
            "newStatus": "to research",
            "id": "POI-3672",
            "title": "cursor researching: CI KPIs on the site management page are wrong",
        }

        self.assertIsNone(build_issue_title_update(event))

    def test_requires_issue_id_and_title(self):
        self.assertIsNone(
            build_issue_title_update(
                {
                    "trigger": "status_changed",
                    "newStatus": "to research",
                    "id": "POI-3672",
                }
            )
        )
        self.assertIsNone(
            build_issue_title_update(
                {
                    "trigger": "status_changed",
                    "newStatus": "to research",
                    "title": "CI KPIs on the site management page are wrong",
                }
            )
        )

    def test_ignores_non_mapping_payloads(self):
        self.assertIsNone(build_issue_title_update(None))


if __name__ == "__main__":
    unittest.main()
