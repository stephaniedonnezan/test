import unittest

from linear_issue_title import (
    RESEARCH_PREFIX,
    maybe_update_issue_title,
    update_issue_title_from_event,
)


class LinearIssueTitleTests(unittest.TestCase):
    def test_adds_cursor_researching_prefix_on_to_research(self) -> None:
        payload = {
            "triggerContext": {
                "trigger": "status_changed",
                "webhookType": "issue",
                "newStatus": "to research",
                "title": "[]UI for incoming POS",
            }
        }

        updated = maybe_update_issue_title(payload)

        self.assertEqual(updated, f"{RESEARCH_PREFIX} - []UI for incoming POS")

    def test_no_change_for_other_statuses(self) -> None:
        payload = {
            "triggerContext": {
                "trigger": "status_changed",
                "webhookType": "issue",
                "newStatus": "In progress",
                "title": "[]UI for incoming POS",
            }
        }

        updated = maybe_update_issue_title(payload)

        self.assertIsNone(updated)

    def test_does_not_duplicate_prefix(self) -> None:
        payload = {
            "triggerContext": {
                "trigger": "status_changed",
                "webhookType": "issue",
                "newStatus": "to research",
                "title": "Cursor researching - []UI for incoming POS",
            }
        }

        updated = maybe_update_issue_title(payload)

        self.assertEqual(updated, "Cursor researching - []UI for incoming POS")

    def test_event_helper_supports_wrapped_payload(self) -> None:
        event = {
            "triggerContext": {
                "trigger": "status_changed",
                "webhookType": "issue",
                "newStatus": "to research",
                "title": "Issue title",
            }
        }

        updated = update_issue_title_from_event(event)

        self.assertEqual(updated, f"{RESEARCH_PREFIX} Issue title")


if __name__ == "__main__":
    unittest.main()
