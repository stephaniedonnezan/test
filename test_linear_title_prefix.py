import unittest

from linear_title_prefix import (
    RESEARCH_PREFIX,
    build_issue_title_update,
    handle_issue_status_changed,
)


class BuildIssueTitleUpdateTest(unittest.TestCase):
    def test_prefixes_issue_title_for_to_research_status_change(self):
        event = {
            "trigger": "status_changed",
            "newStatus": "To Research",
            "id": "POI-2629",
            "title": "Fix Automate website on smaller screens",
        }

        self.assertEqual(
            build_issue_title_update(event),
            {
                "action": "update_issue_title",
                "issueId": "POI-2629",
                "title": f"{RESEARCH_PREFIX}: Fix Automate website on smaller screens",
            },
        )

    def test_accepts_nested_trigger_context_payload(self):
        event = {
            "triggerContext": {
                "trigger": "status_changed",
                "newStatus": "to_research",
                "id": "POI-2629",
                "title": "Fix Automate website on smaller screens",
            }
        }

        self.assertEqual(
            build_issue_title_update(event),
            {
                "action": "update_issue_title",
                "issueId": "POI-2629",
                "title": f"{RESEARCH_PREFIX}: Fix Automate website on smaller screens",
            },
        )

    def test_accepts_linear_issue_updated_with_status_field(self):
        event = {
            "action": "Issue Updated",
            "updatedFields": ["description", "state"],
            "data": {
                "issue": {
                    "identifier": "POI-2629",
                    "title": "Fix Automate website on smaller screens",
                    "state": {"name": "To Research"},
                }
            },
        }

        self.assertEqual(
            build_issue_title_update(event),
            {
                "action": "update_issue_title",
                "issueId": "POI-2629",
                "title": f"{RESEARCH_PREFIX}: Fix Automate website on smaller screens",
            },
        )

    def test_uses_top_level_trigger_metadata_with_nested_issue_data(self):
        event = {
            "trigger": "statusChanged",
            "new_status": "to-research",
            "data": {
                "issue": {
                    "id": "POI-2629",
                    "title": "Fix Automate website on smaller screens",
                }
            },
        }

        self.assertEqual(
            build_issue_title_update(event),
            {
                "action": "update_issue_title",
                "issueId": "POI-2629",
                "title": f"{RESEARCH_PREFIX}: Fix Automate website on smaller screens",
            },
        )

    def test_skips_non_status_change_events(self):
        event = {
            "trigger": "comment_created",
            "newStatus": "To Research",
            "id": "POI-2629",
            "title": "Fix Automate website on smaller screens",
        }

        self.assertIsNone(build_issue_title_update(event))

    def test_skips_issue_updated_without_status_field_change(self):
        event = {
            "action": "Issue Updated",
            "updatedFields": ["title"],
            "newStatus": "To Research",
            "id": "POI-2629",
            "title": "Fix Automate website on smaller screens",
        }

        self.assertIsNone(build_issue_title_update(event))

    def test_skips_status_changes_to_other_statuses(self):
        event = {
            "trigger": "status_changed",
            "newStatus": "Done",
            "id": "POI-2629",
            "title": "Fix Automate website on smaller screens",
        }

        self.assertIsNone(build_issue_title_update(event))

    def test_skips_titles_that_already_have_prefix(self):
        event = {
            "trigger": "status_changed",
            "newStatus": "To Research",
            "id": "POI-2629",
            "title": "cursor researching: Fix Automate website on smaller screens",
        }

        self.assertIsNone(build_issue_title_update(event))

    def test_skips_payloads_missing_issue_id_or_title(self):
        self.assertIsNone(
            build_issue_title_update(
                {
                    "trigger": "status_changed",
                    "newStatus": "To Research",
                    "title": "Fix Automate website on smaller screens",
                }
            )
        )
        self.assertIsNone(
            build_issue_title_update(
                {
                    "trigger": "status_changed",
                    "newStatus": "To Research",
                    "id": "POI-2629",
                }
            )
        )

    def test_alias_matches_primary_entrypoint(self):
        event = {
            "trigger": "status_changed",
            "newStatus": "To Research",
            "issueId": "POI-2629",
            "title": "Fix Automate website on smaller screens",
        }

        self.assertEqual(handle_issue_status_changed(event), build_issue_title_update(event))


if __name__ == "__main__":
    unittest.main()
