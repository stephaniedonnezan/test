import json
import subprocess
import sys
import unittest

from linear_research_title import derive_updated_title
from linear_research_title import title_for_status_change


class TitleForStatusChangeTests(unittest.TestCase):
    def test_adds_cursor_researching_prefix_for_to_research(self) -> None:
        self.assertEqual(
            title_for_status_change(
                title="[]Gather ETS daily prices",
                new_status="to research",
            ),
            "Cursor researching: []Gather ETS daily prices",
        )

    def test_status_matching_ignores_case_and_extra_whitespace(self) -> None:
        self.assertEqual(
            title_for_status_change(
                title="Scope ETS price source",
                new_status="  To   Research ",
            ),
            "Cursor researching: Scope ETS price source",
        )

    def test_leaves_other_statuses_unchanged(self) -> None:
        self.assertEqual(
            title_for_status_change(
                title="Scope ETS price source",
                new_status="In Progress",
            ),
            "Scope ETS price source",
        )

    def test_does_not_duplicate_existing_colon_prefix(self) -> None:
        self.assertEqual(
            title_for_status_change(
                title="Cursor researching: Scope ETS price source",
                new_status="to research",
            ),
            "Cursor researching: Scope ETS price source",
        )

    def test_does_not_duplicate_existing_hyphen_prefix(self) -> None:
        self.assertEqual(
            title_for_status_change(
                title="cursor researching - Scope ETS price source",
                new_status="to research",
            ),
            "cursor researching - Scope ETS price source",
        )


class DeriveUpdatedTitleTests(unittest.TestCase):
    def test_updates_linear_issue_status_changed_payload(self) -> None:
        payload = {
            "automationId": "e6963998-567a-4e55-9dd4-20e63dfd2f11",
            "triggerContext": {
                "triggerType": "linear",
                "webhookType": "issue",
                "trigger": "status_changed",
                "newStatus": "to research",
                "title": "[]Gather ETS daily prices",
                "id": "POI-4483",
            },
        }

        self.assertEqual(
            derive_updated_title(payload),
            "Cursor researching: []Gather ETS daily prices",
        )

    def test_returns_none_when_current_trigger_status_is_not_to_research(self) -> None:
        payload = {
            "triggerContext": {
                "webhookType": "issue",
                "trigger": "status_changed",
                "newStatus": "In Progress",
                "title": "[]Gather ETS daily prices",
            },
        }

        self.assertIsNone(derive_updated_title(payload))

    def test_returns_none_for_non_status_change_issue_events(self) -> None:
        payload = {
            "triggerContext": {
                "webhookType": "issue",
                "trigger": "title_changed",
                "newStatus": "to research",
                "title": "[]Gather ETS daily prices",
            },
        }

        self.assertIsNone(derive_updated_title(payload))

    def test_returns_none_for_non_issue_webhooks(self) -> None:
        payload = {
            "triggerContext": {
                "webhookType": "comment",
                "trigger": "status_changed",
                "newStatus": "to research",
                "title": "[]Gather ETS daily prices",
            },
        }

        self.assertIsNone(derive_updated_title(payload))

    def test_supports_unwrapped_payload_shape(self) -> None:
        payload = {
            "webhookType": "issue",
            "trigger": "status changed",
            "newStatus": "to research",
            "title": "[]Gather ETS daily prices",
        }

        self.assertEqual(
            derive_updated_title(payload),
            "Cursor researching: []Gather ETS daily prices",
        )

    def test_returns_none_for_missing_required_fields(self) -> None:
        self.assertIsNone(derive_updated_title({"triggerContext": {}}))
        self.assertIsNone(
            derive_updated_title(
                {
                    "triggerContext": {
                        "webhookType": "issue",
                        "trigger": "status_changed",
                        "newStatus": "to research",
                    }
                }
            )
        )


class CliTests(unittest.TestCase):
    def test_cli_prints_updated_title_as_json(self) -> None:
        payload = {
            "triggerContext": {
                "webhookType": "issue",
                "trigger": "status_changed",
                "newStatus": "to research",
                "title": "[]Gather ETS daily prices",
            }
        }

        result = subprocess.run(
            [sys.executable, "-m", "linear_research_title"],
            input=json.dumps(payload),
            text=True,
            check=True,
            capture_output=True,
        )

        self.assertEqual(
            json.loads(result.stdout),
            {"updatedTitle": "Cursor researching: []Gather ETS daily prices"},
        )


if __name__ == "__main__":
    unittest.main()
