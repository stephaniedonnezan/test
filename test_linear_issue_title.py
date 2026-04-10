import json
import unittest

from linear_issue_title import PREFIX, update_issue_title


class UpdateIssueTitleTests(unittest.TestCase):
    def test_prefixes_title_on_to_research_status_change(self) -> None:
        payload = {
            "triggerContext": {
                "trigger": "status_changed",
                "newStatus": "to research",
                "title": "Header Refinement",
            }
        }

        self.assertEqual(
            update_issue_title(payload),
            f"{PREFIX} - Header Refinement",
        )

    def test_does_not_change_title_for_other_status(self) -> None:
        payload = {
            "triggerContext": {
                "trigger": "status_changed",
                "newStatus": "Done",
                "title": "Header Refinement",
            }
        }

        self.assertEqual(update_issue_title(payload), "Header Refinement")

    def test_does_not_change_title_for_other_trigger(self) -> None:
        payload = {
            "triggerContext": {
                "trigger": "issue_created",
                "newStatus": "to research",
                "title": "Header Refinement",
            }
        }

        self.assertEqual(update_issue_title(payload), "Header Refinement")

    def test_does_not_duplicate_prefix(self) -> None:
        payload = {
            "triggerContext": {
                "trigger": "status_changed",
                "newStatus": "to research",
                "title": "Cursor researching - Header Refinement",
            }
        }

        self.assertEqual(
            update_issue_title(payload),
            "Cursor researching - Header Refinement",
        )

    def test_supports_root_level_payload(self) -> None:
        payload = {
            "trigger": "status_changed",
            "newStatus": "to research",
            "title": "Header Refinement",
        }

        self.assertEqual(
            update_issue_title(payload),
            "Cursor researching - Header Refinement",
        )

    def test_cli_output_shape(self) -> None:
        payload = {
            "triggerContext": {
                "trigger": "status_changed",
                "newStatus": "to research",
                "title": "Header Refinement",
            }
        }
        expected = {"updatedTitle": "Cursor researching - Header Refinement"}

        self.assertEqual(
            json.loads(json.dumps({"updatedTitle": update_issue_title(payload)})),
            expected,
        )


if __name__ == "__main__":
    unittest.main()
