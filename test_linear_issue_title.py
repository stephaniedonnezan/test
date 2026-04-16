import unittest

from linear_issue_title import apply_status_change_to_issue_payload
from linear_issue_title import add_researching_to_issue_title


class AddResearchingToIssueTitleTests(unittest.TestCase):
    def test_adds_prefix_when_status_is_to_research(self) -> None:
        self.assertEqual(
            add_researching_to_issue_title(
                "[PoS Addresses] Addresses not reflected correctly",
                "to research",
            ),
            "Cursor researching - [PoS Addresses] Addresses not reflected correctly",
        )

    def test_adds_prefix_case_insensitive_status(self) -> None:
        self.assertEqual(
            add_researching_to_issue_title("Issue title", "To Research"),
            "Cursor researching - Issue title",
        )

    def test_does_not_change_title_for_other_statuses(self) -> None:
        title = "Issue title"
        self.assertEqual(add_researching_to_issue_title(title, "In Progress"), title)

    def test_does_not_duplicate_prefix(self) -> None:
        title = "Cursor researching - Existing title"
        self.assertEqual(add_researching_to_issue_title(title, "to research"), title)


class ApplyStatusChangeToIssuePayloadTests(unittest.TestCase):
    def test_updates_linear_status_changed_payload_title(self) -> None:
        payload = {
            "triggerContext": {
                "triggerType": "linear",
                "trigger": "status_changed",
                "newStatus": "to research",
                "title": "Investigate address mismatch",
            }
        }

        updated = apply_status_change_to_issue_payload(payload)
        self.assertEqual(
            updated["triggerContext"]["title"],
            "Cursor researching - Investigate address mismatch",
        )
        self.assertEqual(
            payload["triggerContext"]["title"],
            "Investigate address mismatch",
        )

    def test_keeps_payload_unchanged_when_not_linear_status_change(self) -> None:
        payload = {
            "triggerContext": {
                "triggerType": "linear",
                "trigger": "created",
                "newStatus": "to research",
                "title": "Investigate address mismatch",
            }
        }
        self.assertEqual(apply_status_change_to_issue_payload(payload), payload)


if __name__ == "__main__":
    unittest.main()
