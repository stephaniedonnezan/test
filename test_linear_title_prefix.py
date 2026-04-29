import unittest

from linear_title_prefix import build_issue_title_update


class BuildIssueTitleUpdateTest(unittest.TestCase):
    def test_prefixes_title_when_issue_moves_to_research(self):
        event = {
            "triggerContext": {
                "trigger": "status_changed",
                "newStatus": "to research",
                "id": "POI-2916",
                "title": "Why do we check qualified input?",
            }
        }

        self.assertEqual(
            build_issue_title_update(event),
            {
                "action": "update_issue_title",
                "issueId": "POI-2916",
                "title": "Cursor researching: Why do we check qualified input?",
            },
        )

    def test_accepts_flat_payload(self):
        event = {
            "trigger": "status_changed",
            "newStatus": "to research",
            "id": "POI-2916",
            "title": "Research methane behavior",
        }

        self.assertEqual(
            build_issue_title_update(event),
            {
                "action": "update_issue_title",
                "issueId": "POI-2916",
                "title": "Cursor researching: Research methane behavior",
            },
        )

    def test_accepts_issue_id_when_id_is_absent(self):
        event = {
            "triggerContext": {
                "trigger": "status_changed",
                "newStatus": "to research",
                "issueId": "POI-2916",
                "title": "Research methane behavior",
            }
        }

        self.assertEqual(
            build_issue_title_update(event),
            {
                "action": "update_issue_title",
                "issueId": "POI-2916",
                "title": "Cursor researching: Research methane behavior",
            },
        )

    def test_falls_back_to_status_when_new_status_is_missing(self):
        event = {
            "triggerContext": {
                "trigger": "status_changed",
                "status": "To Research",
                "id": "POI-2916",
                "title": "Research methane behavior",
            }
        }

        self.assertEqual(
            build_issue_title_update(event),
            {
                "action": "update_issue_title",
                "issueId": "POI-2916",
                "title": "Cursor researching: Research methane behavior",
            },
        )

    def test_normalizes_status_case_and_separators(self):
        matching_statuses = [
            "To Research",
            "to_research",
            "to-research",
            "  TO   RESEARCH  ",
        ]

        for status in matching_statuses:
            with self.subTest(status=status):
                event = {
                    "triggerContext": {
                        "trigger": "status_changed",
                        "newStatus": status,
                        "id": "POI-2916",
                        "title": "Research methane behavior",
                    }
                }

                self.assertEqual(
                    build_issue_title_update(event),
                    {
                        "action": "update_issue_title",
                        "issueId": "POI-2916",
                        "title": "Cursor researching: Research methane behavior",
                    },
                )

    def test_normalizes_trigger_case_and_separators(self):
        event = {
            "triggerContext": {
                "trigger": "Status Changed",
                "newStatus": "to research",
                "id": "POI-2916",
                "title": "Research methane behavior",
            }
        }

        self.assertEqual(
            build_issue_title_update(event),
            {
                "action": "update_issue_title",
                "issueId": "POI-2916",
                "title": "Cursor researching: Research methane behavior",
            },
        )

    def test_ignores_other_statuses(self):
        event = {
            "triggerContext": {
                "trigger": "status_changed",
                "newStatus": "Canceled",
                "id": "POI-2916",
                "title": "Research methane behavior",
            }
        }

        self.assertIsNone(build_issue_title_update(event))

    def test_ignores_other_triggers(self):
        event = {
            "triggerContext": {
                "trigger": "issue_created",
                "newStatus": "to research",
                "id": "POI-2916",
                "title": "Research methane behavior",
            }
        }

        self.assertIsNone(build_issue_title_update(event))

    def test_does_not_duplicate_existing_prefix(self):
        event = {
            "triggerContext": {
                "trigger": "status_changed",
                "newStatus": "to research",
                "id": "POI-2916",
                "title": "Cursor researching: Research methane behavior",
            }
        }

        self.assertIsNone(build_issue_title_update(event))

    def test_existing_prefix_check_is_case_insensitive(self):
        event = {
            "triggerContext": {
                "trigger": "status_changed",
                "newStatus": "to research",
                "id": "POI-2916",
                "title": "cursor RESEARCHING - Research methane behavior",
            }
        }

        self.assertIsNone(build_issue_title_update(event))

    def test_trims_title_before_prefixing(self):
        event = {
            "triggerContext": {
                "trigger": "status_changed",
                "newStatus": "to research",
                "id": "POI-2916",
                "title": "  Research methane behavior  ",
            }
        }

        self.assertEqual(
            build_issue_title_update(event),
            {
                "action": "update_issue_title",
                "issueId": "POI-2916",
                "title": "Cursor researching: Research methane behavior",
            },
        )

    def test_ignores_missing_issue_id_or_title(self):
        base_context = {
            "trigger": "status_changed",
            "newStatus": "to research",
            "id": "POI-2916",
            "title": "Research methane behavior",
        }

        for key in ("id", "title"):
            with self.subTest(key=key):
                context = dict(base_context)
                context.pop(key)

                self.assertIsNone(
                    build_issue_title_update({"triggerContext": context})
                )

    def test_ignores_non_mapping_payloads(self):
        for event in (None, [], "status_changed"):
            with self.subTest(event=event):
                self.assertIsNone(build_issue_title_update(event))


if __name__ == "__main__":
    unittest.main()
