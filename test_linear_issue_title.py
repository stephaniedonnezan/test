import unittest

from linear_issue_title import RESEARCHING_MARKER, maybe_update_issue_title, updated_title_for_status_change


class MaybeUpdateIssueTitleTests(unittest.TestCase):
    def test_adds_marker_when_status_changes_to_to_research(self) -> None:
        payload = {
            "triggerContext": {
                "trigger": "status_changed",
                "newStatus": "to research",
                "title": "Investigate endpoint retries",
            }
        }

        updated = maybe_update_issue_title(payload)

        self.assertEqual(updated, f"{RESEARCHING_MARKER} - Investigate endpoint retries")

    def test_does_not_update_for_other_statuses(self) -> None:
        payload = {
            "triggerContext": {
                "trigger": "status_changed",
                "newStatus": "Backlog",
                "title": "Investigate endpoint retries",
            }
        }

        updated = maybe_update_issue_title(payload)

        self.assertIsNone(updated)

    def test_does_not_duplicate_existing_marker(self) -> None:
        payload = {
            "triggerContext": {
                "trigger": "status_changed",
                "newStatus": "to research",
                "title": "Cursor researching - Investigate endpoint retries",
            }
        }

        updated = maybe_update_issue_title(payload)

        self.assertEqual(updated, "Cursor researching - Investigate endpoint retries")

    def test_accepts_root_level_context(self) -> None:
        payload = {
            "trigger": "status_changed",
            "newStatus": "to research",
            "title": "Root payload title",
        }

        updated = maybe_update_issue_title(payload)

        self.assertEqual(updated, f"{RESEARCHING_MARKER} - Root payload title")


class UpdatedTitleForStatusChangeTests(unittest.TestCase):
    def test_returns_none_when_title_already_prefixed(self) -> None:
        payload = {
            "newStatus": "to research",
            "title": "Cursor researching: Existing",
        }

        updated = updated_title_for_status_change(payload)

        self.assertIsNone(updated)

    def test_returns_updated_title_for_new_prefix(self) -> None:
        payload = {
            "newStatus": "To Research",
            "title": "Dashboard: Selecting the current year breaks",
        }

        updated = updated_title_for_status_change(payload)

        self.assertEqual(updated, "Cursor researching - Dashboard: Selecting the current year breaks")


if __name__ == "__main__":
    unittest.main()
