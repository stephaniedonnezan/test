import unittest

from linear_issue_title import RESEARCHING_PREFIX, updated_title_for_status_change


class UpdatedTitleForStatusChangeTests(unittest.TestCase):
    def test_adds_prefix_when_status_changes_to_to_research(self) -> None:
        payload = {
            "triggerContext": {
                "trigger": "status_changed",
                "newStatus": "to research",
                "title": "Mass balance from a site disappears when month is closed",
            }
        }

        updated_title = updated_title_for_status_change(payload)

        self.assertEqual(
            updated_title,
            f"{RESEARCHING_PREFIX} - Mass balance from a site disappears when month is closed",
        )

    def test_returns_none_for_other_statuses(self) -> None:
        payload = {
            "triggerContext": {
                "trigger": "status_changed",
                "newStatus": "In Progress",
                "title": "Some issue title",
            }
        }

        self.assertIsNone(updated_title_for_status_change(payload))

    def test_returns_none_when_title_already_prefixed(self) -> None:
        payload = {
            "triggerContext": {
                "trigger": "status_changed",
                "newStatus": "To Research",
                "title": "Cursor researching - Some issue title",
            }
        }

        self.assertIsNone(updated_title_for_status_change(payload))

    def test_accepts_root_level_payload_shape(self) -> None:
        payload = {
            "trigger": "status_changed",
            "newStatus": "to research",
            "title": "Root-level payload title",
        }

        updated_title = updated_title_for_status_change(payload)

        self.assertEqual(updated_title, f"{RESEARCHING_PREFIX} - Root-level payload title")

    def test_ignores_non_status_change_trigger(self) -> None:
        payload = {
            "triggerContext": {
                "trigger": "issue_updated",
                "newStatus": "to research",
                "title": "Some issue title",
            }
        }

        self.assertIsNone(updated_title_for_status_change(payload))


if __name__ == "__main__":
    unittest.main()
