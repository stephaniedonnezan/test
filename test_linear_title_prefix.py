import unittest

from linear_title_prefix import build_issue_title_update


class BuildIssueTitleUpdateTest(unittest.TestCase):
    def test_prefixes_title_for_status_change_to_research(self):
        event = {
            "triggerContext": {
                "trigger": "status_changed",
                "newStatus": "to research",
                "id": "POI-4572",
                "title": "Trader Mass Balance Export Issues",
            }
        }

        self.assertEqual(
            build_issue_title_update(event),
            {
                "action": "update_issue_title",
                "issueId": "POI-4572",
                "title": "Cursor researching: Trader Mass Balance Export Issues",
            },
        )

    def test_accepts_flat_payload(self):
        event = {
            "trigger": "status_changed",
            "newStatus": "to research",
            "id": "POI-4572",
            "title": "Trader Mass Balance Export Issues",
        }

        self.assertEqual(
            build_issue_title_update(event)["title"],
            "Cursor researching: Trader Mass Balance Export Issues",
        )

    def test_falls_back_to_status_when_new_status_is_missing(self):
        event = {
            "triggerContext": {
                "trigger": "status_changed",
                "status": "To Research",
                "id": "POI-4572",
                "title": "Trader Mass Balance Export Issues",
            }
        }

        self.assertEqual(
            build_issue_title_update(event)["title"],
            "Cursor researching: Trader Mass Balance Export Issues",
        )

    def test_accepts_issue_id_alias(self):
        event = {
            "triggerContext": {
                "trigger": "status_changed",
                "newStatus": "to research",
                "issueId": "POI-4572",
                "title": "Trader Mass Balance Export Issues",
            }
        }

        self.assertEqual(build_issue_title_update(event)["issueId"], "POI-4572")

    def test_normalizes_trigger_and_status_variants(self):
        event = {
            "triggerContext": {
                "trigger": "Status Changed",
                "newStatus": "to_research",
                "id": "POI-4572",
                "title": "Trader Mass Balance Export Issues",
            }
        }

        self.assertIsNotNone(build_issue_title_update(event))

    def test_trims_issue_id_and_title(self):
        event = {
            "triggerContext": {
                "trigger": "status_changed",
                "newStatus": "to research",
                "id": "  POI-4572  ",
                "title": "  Trader Mass Balance Export Issues  ",
            }
        }

        self.assertEqual(
            build_issue_title_update(event),
            {
                "action": "update_issue_title",
                "issueId": "POI-4572",
                "title": "Cursor researching: Trader Mass Balance Export Issues",
            },
        )

    def test_skips_non_status_change_events(self):
        event = {
            "triggerContext": {
                "trigger": "comment_created",
                "newStatus": "to research",
                "id": "POI-4572",
                "title": "Trader Mass Balance Export Issues",
            }
        }

        self.assertIsNone(build_issue_title_update(event))

    def test_skips_non_research_status(self):
        event = {
            "triggerContext": {
                "trigger": "status_changed",
                "newStatus": "In Review",
                "id": "POI-4572",
                "title": "Trader Mass Balance Export Issues",
            }
        }

        self.assertIsNone(build_issue_title_update(event))

    def test_skips_already_prefixed_title_case_insensitively(self):
        event = {
            "triggerContext": {
                "trigger": "status_changed",
                "newStatus": "to research",
                "id": "POI-4572",
                "title": "cursor researching: Trader Mass Balance Export Issues",
            }
        }

        self.assertIsNone(build_issue_title_update(event))

    def test_skips_missing_issue_id(self):
        event = {
            "triggerContext": {
                "trigger": "status_changed",
                "newStatus": "to research",
                "title": "Trader Mass Balance Export Issues",
            }
        }

        self.assertIsNone(build_issue_title_update(event))

    def test_skips_missing_title(self):
        event = {
            "triggerContext": {
                "trigger": "status_changed",
                "newStatus": "to research",
                "id": "POI-4572",
            }
        }

        self.assertIsNone(build_issue_title_update(event))

    def test_skips_non_mapping_payload(self):
        self.assertIsNone(build_issue_title_update(None))
        self.assertIsNone(build_issue_title_update("not an event"))


if __name__ == "__main__":
    unittest.main()
