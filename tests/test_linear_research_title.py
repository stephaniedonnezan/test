import unittest

from scripts.linear_research_title import (
    TITLE_PREFIX,
    add_research_prefix,
    build_title_update,
)


class LinearResearchTitleTest(unittest.TestCase):
    def test_builds_update_for_cursor_status_changed_payload(self):
        payload = {
            "triggerContext": {
                "trigger": "status_changed",
                "newStatus": "To Research",
                "id": "POI-4679",
                "title": "Edit Input button missing container logic mass balance",
            }
        }

        update = build_title_update(payload)

        self.assertIsNotNone(update)
        self.assertEqual(update.issue_id, "POI-4679")
        self.assertEqual(
            update.new_title,
            f"{TITLE_PREFIX}: Edit Input button missing container logic mass balance",
        )

    def test_skips_other_statuses(self):
        payload = {
            "triggerContext": {
                "trigger": "status_changed",
                "newStatus": "QA",
                "id": "POI-4679",
                "title": "Edit Input button missing container logic mass balance",
            }
        }

        self.assertIsNone(build_title_update(payload))

    def test_skips_non_status_change_events(self):
        payload = {
            "triggerContext": {
                "trigger": "comment_created",
                "newStatus": "to research",
                "id": "POI-4679",
                "title": "Edit Input button missing container logic mass balance",
            }
        }

        self.assertIsNone(build_title_update(payload))

    def test_skips_titles_that_already_start_with_prefix(self):
        payload = {
            "triggerContext": {
                "trigger": "status_changed",
                "newStatus": "to research",
                "id": "POI-4679",
                "title": "Cursor researching: Existing title",
            }
        }

        self.assertIsNone(build_title_update(payload))

    def test_supports_linear_webhook_payloads(self):
        payload = {
            "action": "update",
            "updatedFrom": {"stateId": "old-state-id"},
            "data": {
                "id": "issue-uuid",
                "identifier": "POI-4679",
                "title": "Investigate mass balance card",
                "state": {"name": "to research"},
            },
        }

        update = build_title_update(payload)

        self.assertIsNotNone(update)
        self.assertEqual(update.issue_id, "issue-uuid")
        self.assertEqual(update.new_title, f"{TITLE_PREFIX}: Investigate mass balance card")

    def test_add_research_prefix_is_idempotent(self):
        self.assertEqual(
            add_research_prefix("cursor researching: Existing title"),
            "cursor researching: Existing title",
        )


if __name__ == "__main__":
    unittest.main()
