import io
import json
import unittest
from contextlib import redirect_stdout

import linear_title_prefix
from linear_title_prefix import build_issue_title_update


class BuildIssueTitleUpdateTest(unittest.TestCase):
    def test_prefixes_flat_status_changed_payload(self):
        event = {
            "trigger": "status_changed",
            "newStatus": "To Research",
            "id": "POI-4683",
            "title": "[Data Insights] three dots for every KPI box but it does nothing",
        }

        self.assertEqual(
            build_issue_title_update(event),
            {
                "action": "update_issue_title",
                "issueId": "POI-4683",
                "title": (
                    "Cursor researching: [Data Insights] three dots for every KPI box "
                    "but it does nothing"
                ),
            },
        )

    def test_prefixes_automation_trigger_context_payload(self):
        event = {
            "automationId": "e6963998-567a-4e55-9dd4-20e63dfd2f11",
            "triggerContext": {
                "trigger": "status_changed",
                "newStatus": "to research",
                "id": "POI-4683",
                "title": "Hide inactive KPI menu affordance",
            },
        }

        self.assertEqual(
            build_issue_title_update(event),
            {
                "action": "update_issue_title",
                "issueId": "POI-4683",
                "title": "Cursor researching: Hide inactive KPI menu affordance",
            },
        )

    def test_ignores_other_statuses(self):
        event = {
            "trigger": "status_changed",
            "newStatus": "Todo",
            "id": "POI-4683",
            "title": "Hide inactive KPI menu affordance",
        }

        self.assertIsNone(build_issue_title_update(event))

    def test_ignores_non_status_change_triggers(self):
        event = {
            "trigger": "comment_created",
            "newStatus": "To Research",
            "id": "POI-4683",
            "title": "Hide inactive KPI menu affordance",
        }

        self.assertIsNone(build_issue_title_update(event))

    def test_does_not_duplicate_existing_prefix(self):
        event = {
            "trigger": "statusChanged",
            "newStatus": "to_research",
            "id": "POI-4683",
            "title": "cursor researching: Hide inactive KPI menu affordance",
        }

        self.assertIsNone(build_issue_title_update(event))

    def test_normalizes_status_and_trigger_variants(self):
        event = {
            "trigger": "statusChanged",
            "newStatus": "toResearch",
            "issueId": "POI-4683",
            "title": "Hide inactive KPI menu affordance",
        }

        self.assertEqual(
            build_issue_title_update(event)["title"],
            "Cursor researching: Hide inactive KPI menu affordance",
        )

    def test_supports_nested_linear_update_payload(self):
        event = {
            "action": "update",
            "updatedFields": ["state"],
            "data": {
                "issue": {
                    "identifier": "POI-4683",
                    "title": "Hide inactive KPI menu affordance",
                    "state": {"name": "To Research"},
                }
            },
        }

        self.assertEqual(
            build_issue_title_update(event),
            {
                "action": "update_issue_title",
                "issueId": "POI-4683",
                "title": "Cursor researching: Hide inactive KPI menu affordance",
            },
        )

    def test_ignores_generic_update_without_status_marker(self):
        event = {
            "action": "update",
            "updatedFields": ["description"],
            "data": {
                "issue": {
                    "identifier": "POI-4683",
                    "title": "Hide inactive KPI menu affordance",
                    "state": {"name": "To Research"},
                }
            },
        }

        self.assertIsNone(build_issue_title_update(event))

    def test_trims_issue_id_and_title(self):
        event = {
            "trigger": "status_changed",
            "newStatus": "To Research",
            "id": " POI-4683 ",
            "title": " Hide inactive KPI menu affordance ",
        }

        self.assertEqual(
            build_issue_title_update(event),
            {
                "action": "update_issue_title",
                "issueId": "POI-4683",
                "title": "Cursor researching: Hide inactive KPI menu affordance",
            },
        )

    def test_requires_issue_id_and_title(self):
        self.assertIsNone(
            build_issue_title_update(
                {"trigger": "status_changed", "newStatus": "To Research", "id": "POI-4683"}
            )
        )
        self.assertIsNone(
            build_issue_title_update(
                {
                    "trigger": "status_changed",
                    "newStatus": "To Research",
                    "title": "Hide inactive KPI menu affordance",
                }
            )
        )


class CliTest(unittest.TestCase):
    def test_main_prints_update_action(self):
        payload = {
            "trigger": "status_changed",
            "newStatus": "To Research",
            "id": "POI-4683",
            "title": "Hide inactive KPI menu affordance",
        }

        stdin = linear_title_prefix.sys.stdin
        linear_title_prefix.sys.stdin = io.StringIO(json.dumps(payload))
        stdout = io.StringIO()
        try:
            with redirect_stdout(stdout):
                self.assertEqual(linear_title_prefix.main(), 0)
        finally:
            linear_title_prefix.sys.stdin = stdin

        self.assertEqual(
            json.loads(stdout.getvalue()),
            {
                "action": "update_issue_title",
                "issueId": "POI-4683",
                "title": "Cursor researching: Hide inactive KPI menu affordance",
            },
        )


if __name__ == "__main__":
    unittest.main()
