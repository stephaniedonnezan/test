import unittest

from linear_issue_title_updater import get_updated_title, should_update_title


class ShouldUpdateTitleTests(unittest.TestCase):
    def test_updates_for_status_changed_new_status_to_research(self) -> None:
        trigger_context = {
            "trigger": "status_changed",
            "newStatus": "to research",
        }
        self.assertTrue(should_update_title(trigger_context))

    def test_updates_with_different_casing_and_spacing(self) -> None:
        trigger_context = {
            "trigger": " STATUS_CHANGED ",
            "newStatus": "  To Research  ",
        }
        self.assertTrue(should_update_title(trigger_context))

    def test_no_update_for_other_status(self) -> None:
        trigger_context = {
            "trigger": "status_changed",
            "newStatus": "in progress",
        }
        self.assertFalse(should_update_title(trigger_context))

    def test_no_update_for_non_status_changed_trigger(self) -> None:
        trigger_context = {
            "trigger": "comment_created",
            "newStatus": "to research",
        }
        self.assertFalse(should_update_title(trigger_context))


class GetUpdatedTitleTests(unittest.TestCase):
    def test_prefixes_title_when_missing(self) -> None:
        self.assertEqual(
            get_updated_title("Issue to investigate"),
            "Cursor researching - Issue to investigate",
        )

    def test_returns_original_when_already_prefixed(self) -> None:
        self.assertEqual(
            get_updated_title("Cursor researching - Issue to investigate"),
            "Cursor researching - Issue to investigate",
        )

    def test_handles_empty_title(self) -> None:
        self.assertEqual(get_updated_title(""), "Cursor researching")


if __name__ == "__main__":
    unittest.main()
