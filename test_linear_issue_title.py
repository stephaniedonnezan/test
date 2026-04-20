import unittest

from linear_issue_title import evaluate_issue_title_update


class EvaluateIssueTitleUpdateTests(unittest.TestCase):
    def test_updates_title_when_status_changes_to_to_research(self) -> None:
        result = evaluate_issue_title_update(
            {
                "triggerContext": {
                    "newStatus": "to research",
                    "title": "Investigate emissions bug",
                }
            }
        )

        self.assertTrue(result.should_update)
        self.assertEqual(result.new_title, "Cursor researching: Investigate emissions bug")

    def test_is_case_insensitive_for_status(self) -> None:
        result = evaluate_issue_title_update(
            {
                "triggerContext": {
                    "newStatus": "To Research",
                    "title": "Investigate emissions bug",
                }
            }
        )

        self.assertTrue(result.should_update)
        self.assertEqual(result.new_title, "Cursor researching: Investigate emissions bug")

    def test_does_not_duplicate_prefix(self) -> None:
        result = evaluate_issue_title_update(
            {
                "triggerContext": {
                    "newStatus": "to research",
                    "title": "Cursor researching: Investigate emissions bug",
                }
            }
        )

        self.assertFalse(result.should_update)
        self.assertEqual(result.new_title, "Cursor researching: Investigate emissions bug")

    def test_does_not_update_on_other_statuses(self) -> None:
        result = evaluate_issue_title_update(
            {
                "triggerContext": {
                    "newStatus": "qa",
                    "title": "Investigate emissions bug",
                }
            }
        )

        self.assertFalse(result.should_update)
        self.assertEqual(result.new_title, "Investigate emissions bug")

    def test_supports_direct_trigger_context_payload(self) -> None:
        result = evaluate_issue_title_update(
            {
                "newStatus": "to research",
                "title": "Investigate emissions bug",
            }
        )

        self.assertTrue(result.should_update)
        self.assertEqual(result.new_title, "Cursor researching: Investigate emissions bug")


if __name__ == "__main__":
    unittest.main()
