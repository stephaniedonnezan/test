import unittest

from linear_issue_title import add_research_prefix, should_prefix_title, updated_title_for_event


class LinearIssueTitleTests(unittest.TestCase):
    def test_should_prefix_when_linear_issue_moves_to_research(self) -> None:
        event = {
            "triggerContext": {
                "triggerType": "linear",
                "webhookType": "issue",
                "trigger": "status_changed",
                "newStatus": "to research",
            }
        }
        self.assertTrue(should_prefix_title(event))

    def test_should_not_prefix_for_other_status(self) -> None:
        event = {
            "triggerContext": {
                "triggerType": "linear",
                "webhookType": "issue",
                "trigger": "status_changed",
                "newStatus": "QA",
            }
        }
        self.assertFalse(should_prefix_title(event))

    def test_add_research_prefix_once(self) -> None:
        title = "Implement Certifhy chip in audit"
        self.assertEqual(
            add_research_prefix(title),
            "Cursor researching - Implement Certifhy chip in audit",
        )
        self.assertEqual(
            add_research_prefix("Cursor researching - Implement Certifhy chip in audit"),
            "Cursor researching - Implement Certifhy chip in audit",
        )

    def test_updated_title_for_event_returns_none_when_irrelevant(self) -> None:
        event = {
            "triggerContext": {
                "triggerType": "linear",
                "webhookType": "issue",
                "trigger": "comment_created",
                "newStatus": "to research",
                "title": "Investigate title update",
            }
        }
        self.assertIsNone(updated_title_for_event(event))

    def test_updated_title_for_event_returns_prefixed_title(self) -> None:
        event = {
            "triggerContext": {
                "triggerType": "linear",
                "webhookType": "issue",
                "trigger": "status_changed",
                "newStatus": "to research",
                "title": "Investigate title update",
            }
        }
        self.assertEqual(
            updated_title_for_event(event),
            "Cursor researching - Investigate title update",
        )


if __name__ == "__main__":
    unittest.main()
