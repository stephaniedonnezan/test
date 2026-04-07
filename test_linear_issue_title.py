import unittest

from linear_issue_title import RESEARCHING_MARKER
from linear_issue_title import maybe_update_issue_title


class MaybeUpdateIssueTitleTests(unittest.TestCase):
    def test_adds_marker_for_to_research(self) -> None:
        payload = {
            "triggerContext": {
                "trigger": "status_changed",
                "newStatus": "to research",
                "title": "Update the generic fullscreen dialogs styles",
            }
        }

        self.assertEqual(
            maybe_update_issue_title(payload),
            f"{RESEARCHING_MARKER}: Update the generic fullscreen dialogs styles",
        )

    def test_ignores_non_status_trigger(self) -> None:
        payload = {
            "triggerContext": {
                "trigger": "issue_created",
                "newStatus": "to research",
                "title": "Update the generic fullscreen dialogs styles",
            }
        }

        self.assertIsNone(maybe_update_issue_title(payload))


if __name__ == "__main__":
    unittest.main()
