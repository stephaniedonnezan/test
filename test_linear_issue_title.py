import unittest

from linear_issue_title import (
    RESEARCHING_PREFIX,
    maybe_update_issue_title,
    updated_title_for_status_change,
    with_researching_prefix,
)


class WithResearchingPrefixTests(unittest.TestCase):
    def test_adds_prefix_when_missing(self) -> None:
        self.assertEqual(
            with_researching_prefix("Investigate endpoint retries"),
            f"{RESEARCHING_PREFIX} - Investigate endpoint retries",
        )

    def test_does_not_duplicate_existing_prefix(self) -> None:
        self.assertEqual(
            with_researching_prefix("Cursor researching - Investigate endpoint retries"),
            "Cursor researching - Investigate endpoint retries",
        )

    def test_replaces_empty_or_placeholder_title(self) -> None:
        self.assertEqual(with_researching_prefix(""), RESEARCHING_PREFIX)
        self.assertEqual(with_researching_prefix("[]"), RESEARCHING_PREFIX)


class MaybeUpdateIssueTitleTests(unittest.TestCase):
    def test_updates_on_status_changed_to_to_research(self) -> None:
        payload = {
            "triggerContext": {
                "trigger": "status_changed",
                "newStatus": "to research",
                "title": "Investigate endpoint retries",
            }
        }

        updated_title = maybe_update_issue_title(payload)

        self.assertEqual(
            updated_title,
            "Cursor researching - Investigate endpoint retries",
        )

    def test_ignores_other_status_changes(self) -> None:
        payload = {
            "triggerContext": {
                "trigger": "status_changed",
                "newStatus": "In Progress",
                "title": "Investigate endpoint retries",
            }
        }

        self.assertIsNone(maybe_update_issue_title(payload))

    def test_ignores_non_status_change_triggers(self) -> None:
        payload = {
            "triggerContext": {
                "trigger": "comment_created",
                "newStatus": "to research",
                "title": "Investigate endpoint retries",
            }
        }

        self.assertIsNone(maybe_update_issue_title(payload))


class UpdatedTitleForStatusChangeTests(unittest.TestCase):
    def test_returns_none_if_title_already_prefixed(self) -> None:
        payload = {
            "triggerContext": {
                "trigger": "status_changed",
                "newStatus": "To Research",
                "title": "Cursor researching: Investigate endpoint retries",
            }
        }

        self.assertIsNone(updated_title_for_status_change(payload))

    def test_accepts_root_level_context(self) -> None:
        payload = {
            "trigger": "status_changed",
            "newStatus": "to research",
            "title": "Root payload title",
        }

        self.assertEqual(
            updated_title_for_status_change(payload),
            "Cursor researching - Root payload title",
        )


if __name__ == "__main__":
    unittest.main()
