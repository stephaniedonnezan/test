import unittest

from linear_title_prefix import build_issue_title_update


class BuildIssueTitleUpdateTests(unittest.TestCase):
    def test_returns_update_for_nested_status_change_to_research(self):
        event = {
            "triggerContext": {
                "trigger": "status_changed",
                "newStatus": "To Research",
                "id": "POI-4559",
                "title": "Transport Events have way to low emissions",
            }
        }

        self.assertEqual(
            build_issue_title_update(event),
            {
                "action": "update_issue_title",
                "issueId": "POI-4559",
                "title": "Cursor researching: Transport Events have way to low emissions",
            },
        )

    def test_returns_update_for_flat_status_change_to_research(self):
        event = {
            "trigger": "status-changed",
            "newStatus": "to_research",
            "id": "POI-4559",
            "title": "Transport Events have way to low emissions",
        }

        result = build_issue_title_update(event)

        self.assertEqual(result["title"], "Cursor researching: Transport Events have way to low emissions")

    def test_falls_back_to_status_when_new_status_is_absent(self):
        event = {
            "triggerContext": {
                "trigger": "status changed",
                "status": "TO RESEARCH",
                "id": "POI-4559",
                "title": "Research transport emissions",
            }
        }

        result = build_issue_title_update(event)

        self.assertEqual(result["issueId"], "POI-4559")
        self.assertEqual(result["title"], "Cursor researching: Research transport emissions")

    def test_uses_issue_id_alias_when_id_is_absent(self):
        event = {
            "triggerContext": {
                "trigger": "status_changed",
                "newStatus": "to research",
                "issueId": "POI-4559",
                "title": "Research transport emissions",
            }
        }

        self.assertEqual(build_issue_title_update(event)["issueId"], "POI-4559")

    def test_trims_title_before_prefixing(self):
        event = {
            "triggerContext": {
                "trigger": "status_changed",
                "newStatus": "to research",
                "id": "POI-4559",
                "title": "  Research transport emissions  ",
            }
        }

        self.assertEqual(
            build_issue_title_update(event)["title"],
            "Cursor researching: Research transport emissions",
        )

    def test_skips_issue_that_already_has_prefix(self):
        event = {
            "triggerContext": {
                "trigger": "status_changed",
                "newStatus": "to research",
                "id": "POI-4559",
                "title": "Cursor researching: Research transport emissions",
            }
        }

        self.assertIsNone(build_issue_title_update(event))

    def test_skips_existing_prefix_case_insensitively(self):
        event = {
            "triggerContext": {
                "trigger": "status_changed",
                "newStatus": "to research",
                "id": "POI-4559",
                "title": "cursor Researching - Research transport emissions",
            }
        }

        self.assertIsNone(build_issue_title_update(event))

    def test_skips_non_status_change_trigger(self):
        event = {
            "triggerContext": {
                "trigger": "comment_created",
                "newStatus": "to research",
                "id": "POI-4559",
                "title": "Research transport emissions",
            }
        }

        self.assertIsNone(build_issue_title_update(event))

    def test_skips_statuses_other_than_to_research(self):
        event = {
            "triggerContext": {
                "trigger": "status_changed",
                "newStatus": "Done",
                "id": "POI-4559",
                "title": "Research transport emissions",
            }
        }

        self.assertIsNone(build_issue_title_update(event))

    def test_skips_when_required_issue_fields_are_missing(self):
        missing_id = {
            "triggerContext": {
                "trigger": "status_changed",
                "newStatus": "to research",
                "title": "Research transport emissions",
            }
        }
        missing_title = {
            "triggerContext": {
                "trigger": "status_changed",
                "newStatus": "to research",
                "id": "POI-4559",
            }
        }

        self.assertIsNone(build_issue_title_update(missing_id))
        self.assertIsNone(build_issue_title_update(missing_title))

    def test_skips_non_mapping_payloads(self):
        self.assertIsNone(build_issue_title_update(None))
        self.assertIsNone(build_issue_title_update("not an event"))


if __name__ == "__main__":
    unittest.main()
