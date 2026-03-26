import unittest

from linear_issue_title import (
    RESEARCH_PREFIX,
    prefix_research_title,
    should_prefix_research_title,
    update_issue_title_from_event,
)


class LinearIssueTitleTests(unittest.TestCase):
    def test_should_prefix_only_for_issue_status_changed_to_research(self) -> None:
        self.assertTrue(
            should_prefix_research_title(
                {
                    "trigger": "status_changed",
                    "webhookType": "issue",
                    "newStatus": "to research",
                }
            )
        )
        self.assertFalse(
            should_prefix_research_title(
                {
                    "trigger": "status_changed",
                    "webhookType": "issue",
                    "newStatus": "Todo",
                }
            )
        )
        self.assertFalse(
            should_prefix_research_title(
                {
                    "trigger": "comment_created",
                    "webhookType": "issue",
                    "newStatus": "to research",
                }
            )
        )

    def test_prefix_research_title_is_idempotent(self) -> None:
        title = "[MB Export] Incoming PoS number and outgoing PoS number"
        prefixed = prefix_research_title(title)
        self.assertEqual(prefixed, f"{RESEARCH_PREFIX} {title}")
        self.assertEqual(prefix_research_title(prefixed), prefixed)

    def test_update_issue_title_from_event(self) -> None:
        event = {
            "triggerContext": {
                "trigger": "status_changed",
                "webhookType": "issue",
                "newStatus": "to research",
                "title": "Example issue title",
            }
        }
        self.assertEqual(
            update_issue_title_from_event(event),
            f"{RESEARCH_PREFIX} Example issue title",
        )

    def test_update_issue_title_from_event_accepts_root_context(self) -> None:
        event = {
            "trigger": "status_changed",
            "newStatus": "to research",
            "title": "Root context title",
        }
        self.assertEqual(
            update_issue_title_from_event(event),
            f"{RESEARCH_PREFIX} Root context title",
        )

    def test_update_issue_title_from_event_returns_none_when_noop(self) -> None:
        event = {
            "triggerContext": {
                "trigger": "status_changed",
                "webhookType": "issue",
                "newStatus": "Todo",
                "title": "Example issue title",
            }
        }
        self.assertIsNone(update_issue_title_from_event(event))


if __name__ == "__main__":
    unittest.main()
