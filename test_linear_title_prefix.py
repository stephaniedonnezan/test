import unittest

from linear_title_prefix import derive_updated_title
from linear_title_prefix import update_issue_title_for_status


class UpdateIssueTitleForStatusTests(unittest.TestCase):
    def test_adds_prefix_for_to_research(self) -> None:
        self.assertEqual(
            update_issue_title_for_status(
                title="Integration tests + error handling polish",
                new_status="to research",
            ),
            "Cursor researching: Integration tests + error handling polish",
        )

    def test_status_match_is_case_and_whitespace_insensitive(self) -> None:
        self.assertEqual(
            update_issue_title_for_status(
                title="Some issue",
                new_status="  To   Research ",
            ),
            "Cursor researching: Some issue",
        )

    def test_no_change_for_other_status(self) -> None:
        self.assertEqual(
            update_issue_title_for_status(
                title="Some issue",
                new_status="Todo",
            ),
            "Some issue",
        )

    def test_does_not_duplicate_existing_prefix_colon(self) -> None:
        self.assertEqual(
            update_issue_title_for_status(
                title="Cursor researching: Some issue",
                new_status="to research",
            ),
            "Cursor researching: Some issue",
        )

    def test_does_not_duplicate_existing_prefix_hyphen(self) -> None:
        self.assertEqual(
            update_issue_title_for_status(
                title="cursor researching - Some issue",
                new_status="to research",
            ),
            "cursor researching - Some issue",
        )


class DeriveUpdatedTitleTests(unittest.TestCase):
    def test_returns_updated_title_when_payload_matches(self) -> None:
        payload = {
            "triggerContext": {
                "newStatus": "to research",
                "title": "Issue title",
            }
        }

        self.assertEqual(
            derive_updated_title(payload),
            "Cursor researching: Issue title",
        )

    def test_supports_raw_payload_shape(self) -> None:
        payload = {
            "newStatus": "to research",
            "title": "Issue title",
        }

        self.assertEqual(
            derive_updated_title(payload),
            "Cursor researching: Issue title",
        )

    def test_ignores_non_status_changed_triggers(self) -> None:
        payload = {
            "triggerContext": {
                "trigger": "issue_created",
                "newStatus": "to research",
                "title": "Issue title",
            }
        }

        self.assertIsNone(derive_updated_title(payload))

    def test_returns_none_when_no_update_needed(self) -> None:
        payload = {
            "triggerContext": {
                "newStatus": "Todo",
                "title": "Issue title",
            }
        }

        self.assertIsNone(derive_updated_title(payload))

    def test_returns_none_for_invalid_payload(self) -> None:
        self.assertIsNone(derive_updated_title({"triggerContext": "bad"}))
        self.assertIsNone(derive_updated_title({"triggerContext": {}}))


if __name__ == "__main__":
    unittest.main()
