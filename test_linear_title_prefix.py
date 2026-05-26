import io
import json
import unittest
from contextlib import redirect_stdout
from unittest.mock import patch

from linear_title_prefix import build_issue_title_update, main


class BuildIssueTitleUpdateTest(unittest.TestCase):
    def test_prefixes_title_for_status_changed_to_research(self) -> None:
        event = {
            "triggerContext": {
                "trigger": "status_changed",
                "newStatus": "To Research",
                "id": "POI-4724",
                "title": "2026-05-20-DailyReport",
            }
        }

        self.assertEqual(
            build_issue_title_update(event),
            {
                "action": "update_issue_title",
                "issueId": "POI-4724",
                "title": "Cursor researching: 2026-05-20-DailyReport",
            },
        )

    def test_accepts_nested_linear_issue_payloads(self) -> None:
        event = {
            "action": "update",
            "updatedFields": {"state": {"from": "Todo", "to": "To Research"}},
            "data": {
                "id": "linear-id",
                "identifier": "POI-4703",
                "title": "[Backend] DeliveryTransportSegmentEntity",
                "state": {"name": "To Research"},
            },
        }

        self.assertEqual(
            build_issue_title_update(event),
            {
                "action": "update_issue_title",
                "issueId": "POI-4703",
                "title": "Cursor researching: [Backend] DeliveryTransportSegmentEntity",
            },
        )

    def test_accepts_camel_case_and_separator_status_variants(self) -> None:
        for new_status in ("toResearch", "to_research", "to-research"):
            with self.subTest(new_status=new_status):
                event = {
                    "trigger": "statusChanged",
                    "newStatus": new_status,
                    "issueId": "POI-1",
                    "title": "Research this issue",
                }

                self.assertEqual(
                    build_issue_title_update(event),
                    {
                        "action": "update_issue_title",
                        "issueId": "POI-1",
                        "title": "Cursor researching: Research this issue",
                    },
                )

    def test_ignores_other_status_changes(self) -> None:
        event = {
            "triggerContext": {
                "trigger": "status_changed",
                "newStatus": "Canceled",
                "id": "POI-4724",
                "title": "2026-05-20-DailyReport",
            }
        }

        self.assertIsNone(build_issue_title_update(event))

    def test_ignores_non_status_update_events(self) -> None:
        event = {
            "action": "update",
            "updatedFields": ["description"],
            "data": {
                "identifier": "POI-4702",
                "title": "Detailed Documentation of container events",
                "state": {"name": "To Research"},
            },
        }

        self.assertIsNone(build_issue_title_update(event))

    def test_ignores_titles_that_already_have_prefix(self) -> None:
        event = {
            "trigger": "status_changed",
            "status": "To Research",
            "identifier": "POI-4702",
            "title": "cursor researching: Detailed Documentation",
        }

        self.assertIsNone(build_issue_title_update(event))

    def test_ignores_payloads_without_issue_id_or_title(self) -> None:
        self.assertIsNone(
            build_issue_title_update(
                {"trigger": "status_changed", "newStatus": "To Research"}
            )
        )
        self.assertIsNone(
            build_issue_title_update(
                {
                    "trigger": "status_changed",
                    "newStatus": "To Research",
                    "title": "Needs id",
                }
            )
        )

    def test_main_prints_json_action_when_update_is_needed(self) -> None:
        event = {
            "trigger": "status_changed",
            "newStatus": "To Research",
            "identifier": "POI-99",
            "title": "CLI event",
        }
        stdin = io.StringIO(json.dumps(event))
        stdout = io.StringIO()

        with patch("sys.stdin", stdin), redirect_stdout(stdout):
            self.assertEqual(main(), 0)

        self.assertEqual(
            json.loads(stdout.getvalue()),
            {
                "action": "update_issue_title",
                "issueId": "POI-99",
                "title": "Cursor researching: CLI event",
            },
        )


if __name__ == "__main__":
    unittest.main()
