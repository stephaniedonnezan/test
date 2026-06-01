import json
import subprocess
import sys
import unittest

from linear_title_prefix import (
    TITLE_PREFIX,
    build_issue_title_update,
    handle_issue_status_changed,
    with_title_prefix,
)


class BuildIssueTitleUpdateTest(unittest.TestCase):
    def test_prefixes_cursor_status_changed_payload(self) -> None:
        event = {
            "automationId": "automation-id",
            "triggerContext": {
                "triggerType": "linear",
                "webhookType": "issue",
                "trigger": "status_changed",
                "newStatus": "to research",
                "id": "POI-3901",
                "title": "remove DataSourceManager from QualifiedDeliveriesGenerator",
            },
        }

        self.assertEqual(
            build_issue_title_update(event),
            {
                "action": "update_issue_title",
                "issueId": "POI-3901",
                "title": (
                    "Cursor researching: remove DataSourceManager from "
                    "QualifiedDeliveriesGenerator"
                ),
            },
        )

    def test_normalizes_status_and_trigger_names(self) -> None:
        event = {
            "trigger": "statusChanged",
            "new_status": "To-Research",
            "issueId": "POI-3901",
            "title": "Research qualified deliveries generator dependencies",
        }

        self.assertEqual(
            build_issue_title_update(event),
            {
                "action": "update_issue_title",
                "issueId": "POI-3901",
                "title": (
                    "Cursor researching: Research qualified deliveries generator "
                    "dependencies"
                ),
            },
        )

    def test_ignores_other_statuses(self) -> None:
        event = {
            "triggerContext": {
                "trigger": "status_changed",
                "newStatus": "Done",
                "id": "POI-3901",
                "title": "Research qualified deliveries generator dependencies",
            },
        }

        self.assertIsNone(build_issue_title_update(event))

    def test_ignores_non_status_change_events(self) -> None:
        event = {
            "triggerContext": {
                "trigger": "comment_created",
                "newStatus": "to research",
                "id": "POI-3901",
                "title": "Research qualified deliveries generator dependencies",
            },
        }

        self.assertIsNone(build_issue_title_update(event))

    def test_does_not_duplicate_existing_prefix(self) -> None:
        event = {
            "triggerContext": {
                "trigger": "status_changed",
                "newStatus": "to research",
                "id": "POI-3901",
                "title": "cursor researching: Research qualified deliveries generator",
            },
        }

        self.assertIsNone(build_issue_title_update(event))

    def test_accepts_nested_linear_issue_payload(self) -> None:
        event = {
            "action": "Issue Updated",
            "updatedFields": ["state"],
            "data": {
                "id": "webhook-event-id",
                "issue": {
                    "identifier": "POI-3901",
                    "title": "Research qualified deliveries generator dependencies",
                    "state": {"name": "To Research"},
                },
            },
        }

        self.assertEqual(
            build_issue_title_update(event),
            {
                "action": "update_issue_title",
                "issueId": "POI-3901",
                "title": (
                    "Cursor researching: Research qualified deliveries generator "
                    "dependencies"
                ),
            },
        )

    def test_ignores_issue_updated_without_status_field(self) -> None:
        event = {
            "action": "Issue Updated",
            "updatedFields": ["description"],
            "data": {
                "issue": {
                    "identifier": "POI-3901",
                    "title": "Research qualified deliveries generator dependencies",
                    "state": {"name": "To Research"},
                },
            },
        }

        self.assertIsNone(build_issue_title_update(event))

    def test_requires_issue_id_and_title(self) -> None:
        self.assertIsNone(
            build_issue_title_update(
                {
                    "triggerContext": {
                        "trigger": "status_changed",
                        "newStatus": "to research",
                        "title": "Research qualified deliveries generator dependencies",
                    },
                }
            )
        )
        self.assertIsNone(
            build_issue_title_update(
                {
                    "triggerContext": {
                        "trigger": "status_changed",
                        "newStatus": "to research",
                        "id": "POI-3901",
                    },
                }
            )
        )

    def test_ignores_non_mapping_payloads(self) -> None:
        self.assertIsNone(build_issue_title_update(None))
        self.assertIsNone(build_issue_title_update(["not", "a", "mapping"]))


class TitlePrefixTest(unittest.TestCase):
    def test_with_title_prefix_adds_single_prefix(self) -> None:
        self.assertEqual(
            with_title_prefix("Research qualified deliveries generator"),
            f"{TITLE_PREFIX}: Research qualified deliveries generator",
        )
        self.assertEqual(
            with_title_prefix("Cursor researching - Research qualified deliveries generator"),
            "Cursor researching - Research qualified deliveries generator",
        )
        self.assertEqual(with_title_prefix("   "), TITLE_PREFIX)


class EntrypointTest(unittest.TestCase):
    def test_handler_alias(self) -> None:
        event = {
            "triggerContext": {
                "trigger": "status_changed",
                "newStatus": "to research",
                "id": "POI-3901",
                "title": "Research qualified deliveries generator dependencies",
            },
        }

        self.assertEqual(handle_issue_status_changed(event), build_issue_title_update(event))

    def test_cli_prints_update_action(self) -> None:
        event = {
            "triggerContext": {
                "trigger": "status_changed",
                "newStatus": "to research",
                "id": "POI-3901",
                "title": "Research qualified deliveries generator dependencies",
            },
        }

        result = subprocess.run(
            [sys.executable, "linear_title_prefix.py"],
            check=True,
            input=json.dumps(event),
            text=True,
            capture_output=True,
        )

        self.assertEqual(
            json.loads(result.stdout),
            {
                "action": "update_issue_title",
                "issueId": "POI-3901",
                "title": (
                    "Cursor researching: Research qualified deliveries generator "
                    "dependencies"
                ),
            },
        )


if __name__ == "__main__":
    unittest.main()
