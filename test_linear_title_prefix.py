import unittest

from linear_title_prefix import build_issue_title_update


class BuildIssueTitleUpdateTest(unittest.TestCase):
    def test_prefixes_title_when_status_changes_to_research(self):
        update = build_issue_title_update(
            {
                "triggerContext": {
                    "trigger": "status_changed",
                    "newStatus": "to research",
                    "id": "POI-4561",
                    "title": "Inputs disappear in mass balance view",
                }
            }
        )

        self.assertEqual(
            update,
            {
                "action": "update_issue_title",
                "issueId": "POI-4561",
                "title": "Cursor researching: Inputs disappear in mass balance view",
            },
        )

    def test_ignores_status_changes_to_other_statuses(self):
        update = build_issue_title_update(
            {
                "triggerContext": {
                    "trigger": "status_changed",
                    "newStatus": "Done",
                    "id": "POI-4561",
                    "title": "Inputs disappear in mass balance view",
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
                    "id": "POI-4561",
                    "title": "Inputs disappear in mass balance view",
                }
            }
        )

        self.assertIsNone(update)

    def test_does_not_duplicate_existing_prefix(self):
        update = build_issue_title_update(
            {
                "triggerContext": {
                    "trigger": "status_changed",
                    "newStatus": "to research",
                    "id": "POI-4561",
                    "title": "cursor researching: Inputs disappear in mass balance view",
                }
            }
        )

        self.assertIsNone(update)

    def test_accepts_case_and_separator_variants(self):
        update = build_issue_title_update(
            {
                "triggerContext": {
                    "trigger": "statusChanged",
                    "newStatus": "To_Research",
                    "id": "POI-4561",
                    "title": "Inputs disappear in mass balance view",
                }
            }
        )

        self.assertEqual(
            update["title"],
            "Cursor researching: Inputs disappear in mass balance view",
        )

    def test_reads_nested_linear_issue_payload(self):
        update = build_issue_title_update(
            {
                "action": "statusChanged",
                "data": {
                    "issue": {
                        "identifier": "POI-4561",
                        "title": "Inputs disappear in mass balance view",
                        "state": {"name": "to research"},
                    }
                },
            }
        )

        self.assertEqual(
            update,
            {
                "action": "update_issue_title",
                "issueId": "POI-4561",
                "title": "Cursor researching: Inputs disappear in mass balance view",
            },
        )

    def test_returns_none_without_required_issue_fields(self):
        update = build_issue_title_update(
            {
                "triggerContext": {
                    "trigger": "status_changed",
                    "newStatus": "to research",
                    "title": "Inputs disappear in mass balance view",
                }
            }
        )

        self.assertIsNone(update)


if __name__ == "__main__":
    unittest.main()
