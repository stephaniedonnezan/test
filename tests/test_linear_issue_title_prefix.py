import unittest

from src.linear_issue_title_prefix import (
    RESEARCH_PREFIX,
    updated_issue_title,
)


class UpdatedIssueTitleTests(unittest.TestCase):
    def test_adds_prefix_on_to_research_status_change(self) -> None:
        event = {
            "triggerContext": {
                "trigger": "status_changed",
                "newStatus": "to research",
                "title": "[]QA: day ahead grid price can be negative",
            }
        }

        self.assertEqual(
            updated_issue_title(event),
            f"{RESEARCH_PREFIX}: []QA: day ahead grid price can be negative",
        )

    def test_is_case_insensitive_on_new_status_and_trigger(self) -> None:
        event = {
            "triggerContext": {
                "trigger": "STATUS_CHANGED",
                "newStatus": "To Research",
                "title": "Investigate pricing upload",
            }
        }

        self.assertEqual(
            updated_issue_title(event),
            f"{RESEARCH_PREFIX}: Investigate pricing upload",
        )

    def test_does_not_duplicate_prefix(self) -> None:
        event = {
            "triggerContext": {
                "trigger": "status_changed",
                "newStatus": "to research",
                "title": "Cursor researching: Investigate pricing upload",
            }
        }

        self.assertEqual(
            updated_issue_title(event),
            "Cursor researching: Investigate pricing upload",
        )

    def test_returns_none_for_other_status_change(self) -> None:
        event = {
            "triggerContext": {
                "trigger": "status_changed",
                "newStatus": "In Review",
                "title": "Investigate pricing upload",
            }
        }

        self.assertIsNone(updated_issue_title(event))


if __name__ == "__main__":
    unittest.main()
