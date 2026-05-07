import unittest

from linear_title_prefix import build_issue_title_update


class BuildIssueTitleUpdateTest(unittest.TestCase):
    def test_prefixes_title_for_to_research_status_change(self):
        event = {
            "triggerContext": {
                "trigger": "status_changed",
                "newStatus": "to research",
                "id": "POI-3949",
                "title": "Mass Balance Export of traders",
            }
        }

        self.assertEqual(
            build_issue_title_update(event),
            {
                "action": "update_issue_title",
                "issueId": "POI-3949",
                "title": "Cursor researching: Mass Balance Export of traders",
            },
        )

    def test_accepts_linear_data_issue_payload_shape(self):
        event = {
            "action": "statusChanged",
            "data": {
                "issue": {
                    "identifier": "POI-3949",
                    "title": "Mass Balance Export of traders",
                    "state": {"name": "To Research"},
                }
            },
        }

        self.assertEqual(
            build_issue_title_update(event),
            {
                "action": "update_issue_title",
                "issueId": "POI-3949",
                "title": "Cursor researching: Mass Balance Export of traders",
            },
        )

    def test_accepts_status_with_separator_variants(self):
        event = {
            "trigger": "status-changed",
            "new_status": "to_research",
            "issueId": "POI-3949",
            "title": "Mass Balance Export of traders",
        }

        self.assertEqual(
            build_issue_title_update(event)["title"],
            "Cursor researching: Mass Balance Export of traders",
        )

    def test_ignores_non_status_change_events(self):
        event = {
            "trigger": "comment_created",
            "newStatus": "to research",
            "id": "POI-3949",
            "title": "Mass Balance Export of traders",
        }

        self.assertIsNone(build_issue_title_update(event))

    def test_ignores_other_statuses(self):
        event = {
            "trigger": "status_changed",
            "newStatus": "Done",
            "id": "POI-3949",
            "title": "Mass Balance Export of traders",
        }

        self.assertIsNone(build_issue_title_update(event))

    def test_ignores_existing_prefix_case_insensitively(self):
        event = {
            "trigger": "status_changed",
            "newStatus": "to research",
            "id": "POI-3949",
            "title": "cursor researching: Mass Balance Export of traders",
        }

        self.assertIsNone(build_issue_title_update(event))

    def test_requires_issue_id_and_title(self):
        self.assertIsNone(
            build_issue_title_update(
                {"trigger": "status_changed", "newStatus": "to research", "id": "POI-3949"}
            )
        )
        self.assertIsNone(
            build_issue_title_update(
                {
                    "trigger": "status_changed",
                    "newStatus": "to research",
                    "title": "Mass Balance Export of traders",
                }
            )
        )

    def test_safely_ignores_non_mapping_payloads(self):
        self.assertIsNone(build_issue_title_update(None))


if __name__ == "__main__":
    unittest.main()
