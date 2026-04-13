import unittest

from linear_issue_title import update_issue_title


class UpdateIssueTitleTests(unittest.TestCase):
    def test_prefixes_title_when_status_changes_to_research(self) -> None:
        payload = {
            "triggerContext": {
                "trigger": "status_changed",
                "newStatus": "To Research",
                "title": "methanation unit, offtaker from H2 should be Turn2X gmbh on the H2 POS",
            }
        }

        updated = update_issue_title(payload)

        self.assertEqual(
            updated,
            "Cursor researching - methanation unit, offtaker from H2 should be Turn2X gmbh on the H2 POS",
        )

    def test_does_not_update_for_different_status(self) -> None:
        payload = {
            "triggerContext": {
                "trigger": "status_changed",
                "newStatus": "In Progress",
                "title": "Example issue title",
            }
        }

        self.assertEqual(update_issue_title(payload), "Example issue title")

    def test_does_not_update_for_non_status_trigger(self) -> None:
        payload = {
            "triggerContext": {
                "trigger": "issue_created",
                "newStatus": "To Research",
                "title": "Example issue title",
            }
        }

        self.assertEqual(update_issue_title(payload), "Example issue title")

    def test_avoids_duplicate_prefix(self) -> None:
        payload = {
            "triggerContext": {
                "trigger": "status_changed",
                "newStatus": "To Research",
                "title": "Cursor researching - Existing title",
            }
        }

        self.assertEqual(update_issue_title(payload), "Cursor researching - Existing title")

    def test_supports_root_level_trigger_payload(self) -> None:
        payload = {
            "trigger": "status_changed",
            "newStatus": "To Research",
            "title": "Root level payload title",
        }

        self.assertEqual(update_issue_title(payload), "Cursor researching - Root level payload title")


if __name__ == "__main__":
    unittest.main()
