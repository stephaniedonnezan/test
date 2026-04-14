import unittest

from linear_issue_title import compute_updated_title


class ComputeUpdatedTitleTests(unittest.TestCase):
    def test_adds_prefix_when_status_changes_to_research(self) -> None:
        payload = {
            "triggerContext": {
                "trigger": "status_changed",
                "newStatus": "To research",
                "title": "My issue",
            }
        }

        self.assertEqual(
            compute_updated_title(payload),
            "Cursor researching - My issue",
        )

    def test_returns_none_for_other_status(self) -> None:
        payload = {
            "triggerContext": {
                "trigger": "status_changed",
                "newStatus": "Todo",
                "title": "My issue",
            }
        }

        self.assertIsNone(compute_updated_title(payload))

    def test_returns_none_for_non_status_change_trigger(self) -> None:
        payload = {
            "triggerContext": {
                "trigger": "comment_created",
                "newStatus": "To research",
                "title": "My issue",
            }
        }

        self.assertIsNone(compute_updated_title(payload))

    def test_does_not_double_prefix(self) -> None:
        payload = {
            "triggerContext": {
                "trigger": "status_changed",
                "newStatus": "to research",
                "title": "Cursor researching - Existing",
            }
        }

        self.assertEqual(
            compute_updated_title(payload),
            "Cursor researching - Existing",
        )


if __name__ == "__main__":
    unittest.main()
