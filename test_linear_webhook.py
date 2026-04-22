import unittest

from linear_webhook import apply_issue_title_rules


class ApplyIssueTitleRulesTests(unittest.TestCase):
    def test_adds_cursor_researching_on_to_research_status_change(self) -> None:
        payload = {
            "triggerContext": {
                "trigger": "status_changed",
                "newStatus": "to research",
                "title": "Develop solution for fluctuating LHV in natural gas mixture",
            }
        }

        updated = apply_issue_title_rules(payload)

        self.assertEqual(
            updated["triggerContext"]["title"],
            "Cursor researching - Develop solution for fluctuating LHV in natural gas mixture",
        )

    def test_is_idempotent_when_prefix_already_present(self) -> None:
        payload = {
            "triggerContext": {
                "trigger": "status_changed",
                "newStatus": "to research",
                "title": "Cursor researching - Existing title",
            }
        }

        updated = apply_issue_title_rules(payload)

        self.assertEqual(updated["triggerContext"]["title"], "Cursor researching - Existing title")

    def test_does_not_change_other_status(self) -> None:
        payload = {
            "triggerContext": {
                "trigger": "status_changed",
                "newStatus": "Canceled",
                "title": "Develop solution",
            }
        }

        updated = apply_issue_title_rules(payload)

        self.assertEqual(updated["triggerContext"]["title"], "Develop solution")

    def test_does_not_change_when_not_status_changed_trigger(self) -> None:
        payload = {
            "triggerContext": {
                "trigger": "issue_updated",
                "newStatus": "to research",
                "title": "Develop solution",
            }
        }

        updated = apply_issue_title_rules(payload)

        self.assertEqual(updated["triggerContext"]["title"], "Develop solution")


if __name__ == "__main__":
    unittest.main()
