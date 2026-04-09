import unittest

from linear_issue_title import RESEARCH_PREFIX
from linear_issue_title import add_research_prefix
from linear_issue_title import derive_updated_title
from linear_issue_title import should_prefix_title


class ShouldPrefixTitleTests(unittest.TestCase):
    def test_requires_issue_webhook_type(self) -> None:
        self.assertFalse(
            should_prefix_title(
                {
                    "webhookType": "project",
                    "trigger": "status_changed",
                    "newStatus": "to research",
                }
            )
        )

    def test_requires_status_change_trigger(self) -> None:
        self.assertFalse(
            should_prefix_title(
                {
                    "webhookType": "issue",
                    "trigger": "comment_created",
                    "newStatus": "to research",
                }
            )
        )

    def test_handles_normalized_trigger_and_status(self) -> None:
        self.assertTrue(
            should_prefix_title(
                {
                    "webhookType": "issue",
                    "trigger": "Status Changed",
                    "newStatus": "  To   Research ",
                }
            )
        )

    def test_returns_false_for_non_research_status(self) -> None:
        self.assertFalse(
            should_prefix_title(
                {
                    "webhookType": "issue",
                    "trigger": "status_changed",
                    "newStatus": "Canceled",
                }
            )
        )


class AddResearchPrefixTests(unittest.TestCase):
    def test_adds_prefix_for_unprefixed_titles(self) -> None:
        self.assertEqual(
            add_research_prefix("Check filter and ordering consistency on tables"),
            f"{RESEARCH_PREFIX} - Check filter and ordering consistency on tables",
        )

    def test_does_not_duplicate_existing_prefix(self) -> None:
        self.assertEqual(
            add_research_prefix("cursor researching: Existing title"),
            "cursor researching: Existing title",
        )


class DeriveUpdatedTitleTests(unittest.TestCase):
    def test_supports_cursor_trigger_context_wrapper(self) -> None:
        payload = {
            "triggerContext": {
                "webhookType": "issue",
                "trigger": "status_changed",
                "newStatus": "to research",
                "title": "Check filter and ordering consistency on tables",
            }
        }

        self.assertEqual(
            derive_updated_title(payload),
            "Cursor researching - Check filter and ordering consistency on tables",
        )

    def test_returns_none_when_status_is_not_to_research(self) -> None:
        payload = {
            "triggerContext": {
                "webhookType": "issue",
                "trigger": "status_changed",
                "newStatus": "Canceled",
                "title": "Check filter and ordering consistency on tables",
            }
        }

        self.assertIsNone(derive_updated_title(payload))

    def test_returns_none_for_invalid_payload(self) -> None:
        self.assertIsNone(derive_updated_title({"triggerContext": {"newStatus": "to research"}}))


if __name__ == "__main__":
    unittest.main()
