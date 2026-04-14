import unittest

from linear_title_prefix import (
    RESEARCH_TITLE_PREFIX,
    apply_research_title_prefix,
    update_title_for_status,
)


class LinearTitlePrefixTests(unittest.TestCase):
    def test_adds_prefix_when_status_is_to_research(self) -> None:
        title = update_title_for_status("Extract audit log", "to research")
        self.assertEqual(title, f"{RESEARCH_TITLE_PREFIX} - Extract audit log")

    def test_status_check_is_case_insensitive(self) -> None:
        title = update_title_for_status("Extract audit log", "  To Research ")
        self.assertEqual(title, f"{RESEARCH_TITLE_PREFIX} - Extract audit log")

    def test_does_not_duplicate_existing_prefix(self) -> None:
        original = f"{RESEARCH_TITLE_PREFIX} - Extract audit log"
        title = update_title_for_status(original, "to research")
        self.assertEqual(title, original)

    def test_keeps_original_title_for_other_status(self) -> None:
        original = "Extract audit log"
        title = update_title_for_status(original, "in progress")
        self.assertEqual(title, original)

    def test_updates_event_payload_context_title(self) -> None:
        event = {
            "triggerContext": {"newStatus": "to research", "title": "Extract audit log"}
        }
        updated = apply_research_title_prefix(event)
        self.assertEqual(
            updated["triggerContext"]["title"],
            f"{RESEARCH_TITLE_PREFIX} - Extract audit log",
        )
        self.assertEqual(event["triggerContext"]["title"], "Extract audit log")


if __name__ == "__main__":
    unittest.main()
