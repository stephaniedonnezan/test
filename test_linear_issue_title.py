import unittest

from linear_issue_title import RESEARCHING_MARKER, maybe_update_issue_title


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

    def test_replaces_empty_bracket_title_with_marker(self) -> None:
        payload = {
            "triggerContext": {
                "trigger": "status_changed",
                "newStatus": "to research",
                "title": "[]",
            }
        }

        updated = maybe_update_issue_title(payload)

        self.assertEqual(updated, RESEARCHING_MARKER)


if __name__ == "__main__":
    unittest.main()
