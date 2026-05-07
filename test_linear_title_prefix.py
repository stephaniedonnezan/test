import unittest

from linear_title_prefix import build_issue_title_update


class BuildIssueTitleUpdateTest(unittest.TestCase):
    def test_adds_prefix_for_to_research_status_change(self) -> None:
        event = {
            "triggerContext": {
                "trigger": "status_changed",
                "newStatus": "To Research",
                "id": "POI-4625",
                "title": "Potential bug / logic error - delivery ID 7937 - RFNBO content",
            }
        }

        self.assertEqual(
            build_issue_title_update(event),
            {
                "action": "update_issue_title",
                "issueId": "POI-4625",
                "title": (
                    "Cursor researching: "
                    "Potential bug / logic error - delivery ID 7937 - RFNBO content"
                ),
            },
        )

    def test_accepts_nested_linear_issue_payload(self) -> None:
        event = {
            "action": "statusChanged",
            "data": {
                "issue": {
                    "identifier": "POI-4625",
                    "title": "RFNBO content lost",
                    "state": {"name": "to_research"},
                }
            },
        }

        self.assertEqual(
            build_issue_title_update(event),
            {
                "action": "update_issue_title",
                "issueId": "POI-4625",
                "title": "Cursor researching: RFNBO content lost",
            },
        )

    def test_accepts_flat_issue_id_field_and_hyphenated_status(self) -> None:
        event = {
            "webhookType": "status changed",
            "new_status": "to-research",
            "issueId": "POI-4625",
            "title": "RFNBO content lost",
        }

        self.assertEqual(
            build_issue_title_update(event),
            {
                "action": "update_issue_title",
                "issueId": "POI-4625",
                "title": "Cursor researching: RFNBO content lost",
            },
        )

    def test_accepts_camel_case_target_status(self) -> None:
        event = {
            "type": "statusChanged",
            "status": "toResearch",
            "issue_id": "POI-4625",
            "name": "RFNBO content lost",
        }

        self.assertEqual(
            build_issue_title_update(event),
            {
                "action": "update_issue_title",
                "issueId": "POI-4625",
                "title": "Cursor researching: RFNBO content lost",
            },
        )

    def test_does_not_update_for_other_status(self) -> None:
        event = {
            "trigger": "status_changed",
            "newStatus": "In Review",
            "id": "POI-4625",
            "title": "RFNBO content lost",
        }

        self.assertIsNone(build_issue_title_update(event))

    def test_does_not_update_for_other_trigger(self) -> None:
        event = {
            "trigger": "comment_created",
            "newStatus": "to research",
            "id": "POI-4625",
            "title": "RFNBO content lost",
        }

        self.assertIsNone(build_issue_title_update(event))

    def test_does_not_duplicate_existing_prefix(self) -> None:
        event = {
            "trigger": "status_changed",
            "newStatus": "to research",
            "id": "POI-4625",
            "title": "cursor researching: RFNBO content lost",
        }

        self.assertIsNone(build_issue_title_update(event))

    def test_trims_issue_id_and_title(self) -> None:
        event = {
            "trigger": "status_changed",
            "newStatus": "to research",
            "id": " POI-4625 ",
            "title": " RFNBO content lost ",
        }

        self.assertEqual(
            build_issue_title_update(event),
            {
                "action": "update_issue_title",
                "issueId": "POI-4625",
                "title": "Cursor researching: RFNBO content lost",
            },
        )

    def test_requires_issue_id(self) -> None:
        event = {
            "trigger": "status_changed",
            "newStatus": "to research",
            "title": "RFNBO content lost",
        }

        self.assertIsNone(build_issue_title_update(event))

    def test_requires_title(self) -> None:
        event = {
            "trigger": "status_changed",
            "newStatus": "to research",
            "id": "POI-4625",
        }

        self.assertIsNone(build_issue_title_update(event))

    def test_ignores_non_mapping_payload(self) -> None:
        self.assertIsNone(build_issue_title_update(None))


if __name__ == "__main__":
    unittest.main()
