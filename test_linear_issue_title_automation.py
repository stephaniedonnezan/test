import unittest

from linear_issue_title_automation import build_issue_title_update


class BuildIssueTitleUpdateTests(unittest.TestCase):
    def test_prefixes_title_when_status_changes_to_research(self) -> None:
        payload = {
            "triggerContext": {
                "trigger": "status_changed",
                "newStatus": "to research",
                "title": "Addresses not reflected correctly",
            }
        }

        self.assertEqual(
            build_issue_title_update(payload),
            {"title": "Cursor researching - Addresses not reflected correctly"},
        )

    def test_prefixes_title_case_insensitive_status(self) -> None:
        payload = {
            "triggerContext": {
                "trigger": "status_changed",
                "newStatus": "To Research",
                "title": "A title",
            }
        }

        self.assertEqual(
            build_issue_title_update(payload),
            {"title": "Cursor researching - A title"},
        )

    def test_returns_none_for_other_status(self) -> None:
        payload = {
            "triggerContext": {
                "trigger": "status_changed",
                "newStatus": "In Review",
                "title": "A title",
            }
        }

        self.assertIsNone(build_issue_title_update(payload))

    def test_returns_none_for_non_status_change_trigger(self) -> None:
        payload = {
            "triggerContext": {
                "trigger": "issue_created",
                "newStatus": "to research",
                "title": "A title",
            }
        }

        self.assertIsNone(build_issue_title_update(payload))

    def test_returns_none_when_title_already_prefixed(self) -> None:
        payload = {
            "triggerContext": {
                "trigger": "status_changed",
                "newStatus": "to research",
                "title": "Cursor researching - Existing title",
            }
        }

        self.assertIsNone(build_issue_title_update(payload))


if __name__ == "__main__":
    unittest.main()
