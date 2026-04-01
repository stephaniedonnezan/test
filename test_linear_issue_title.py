import unittest

from linear_issue_title import RESEARCHING_MARKER, maybe_update_issue_title


class MaybeUpdateIssueTitleTests(unittest.TestCase):
    def test_adds_marker_when_status_changes_to_to_research(self) -> None:
        payload = {
            "triggerContext": {
                "trigger": "status_changed",
                "newStatus": "to research",
                "title": "Update the generic fullscreen dialogs styles",
            }
        }

        updated = maybe_update_issue_title(payload)

        self.assertEqual(updated, f"{RESEARCHING_MARKER} - Update the generic fullscreen dialogs styles")

    def test_does_not_update_for_other_statuses(self) -> None:
        payload = {
            "triggerContext": {
                "trigger": "status_changed",
                "newStatus": "In Review",
                "title": "Update the generic fullscreen dialogs styles",
            }
        }

        updated = maybe_update_issue_title(payload)

        self.assertIsNone(updated)

    def test_does_not_duplicate_existing_marker(self) -> None:
        payload = {
            "triggerContext": {
                "trigger": "status_changed",
                "newStatus": "to research",
                "title": "Cursor researching - Update the generic fullscreen dialogs styles",
            }
        }

        updated = maybe_update_issue_title(payload)

        self.assertEqual(updated, "Cursor researching - Update the generic fullscreen dialogs styles")

    def test_ignores_non_status_change_trigger(self) -> None:
        payload = {
            "triggerContext": {
                "trigger": "issue_created",
                "newStatus": "to research",
                "title": "Update the generic fullscreen dialogs styles",
            }
        }

        updated = maybe_update_issue_title(payload)

        self.assertIsNone(updated)

    def test_accepts_root_level_payload(self) -> None:
        payload = {
            "trigger": "status_changed",
            "newStatus": "to research",
            "title": "Root payload title",
        }

        updated = maybe_update_issue_title(payload)

        self.assertEqual(updated, f"{RESEARCHING_MARKER} - Root payload title")


if __name__ == "__main__":
    unittest.main()
