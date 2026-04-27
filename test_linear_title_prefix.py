import unittest

from linear_title_prefix import PREFIX, build_issue_title_update


class BuildIssueTitleUpdateTest(unittest.TestCase):
    def test_returns_title_update_for_to_research_status_change(self):
        event = {
            "triggerContext": {
                "trigger": "status_changed",
                "newStatus": "To Research",
                "id": "POI-4220",
                "title": "Lhyfe deployment surplus conversion",
            }
        }

        self.assertEqual(
            build_issue_title_update(event),
            {
                "action": "update_issue_title",
                "issueId": "POI-4220",
                "title": f"{PREFIX}: Lhyfe deployment surplus conversion",
            },
        )

    def test_accepts_flat_payloads(self):
        event = {
            "trigger": "status changed",
            "newStatus": "to-research",
            "id": "POI-4220",
            "title": "Qualify September surpluses",
        }

        self.assertEqual(
            build_issue_title_update(event),
            {
                "action": "update_issue_title",
                "issueId": "POI-4220",
                "title": f"{PREFIX}: Qualify September surpluses",
            },
        )

    def test_falls_back_to_status_when_new_status_is_missing(self):
        event = {
            "triggerContext": {
                "trigger": "STATUS_CHANGED",
                "status": "to research",
                "id": "POI-4220",
                "title": "Convert surplus inputs",
            }
        }

        self.assertEqual(
            build_issue_title_update(event)["title"],
            f"{PREFIX}: Convert surplus inputs",
        )

    def test_returns_none_for_other_statuses(self):
        event = {
            "triggerContext": {
                "trigger": "status_changed",
                "newStatus": "Done",
                "id": "POI-4220",
                "title": "Convert surplus inputs",
            }
        }

        self.assertIsNone(build_issue_title_update(event))

    def test_returns_none_for_other_triggers(self):
        event = {
            "triggerContext": {
                "trigger": "comment_created",
                "newStatus": "to research",
                "id": "POI-4220",
                "title": "Convert surplus inputs",
            }
        }

        self.assertIsNone(build_issue_title_update(event))

    def test_does_not_duplicate_existing_prefix(self):
        event = {
            "triggerContext": {
                "trigger": "status_changed",
                "newStatus": "to research",
                "id": "POI-4220",
                "title": f"{PREFIX}: Convert surplus inputs",
            }
        }

        self.assertIsNone(build_issue_title_update(event))

    def test_existing_prefix_check_is_case_insensitive(self):
        event = {
            "triggerContext": {
                "trigger": "status_changed",
                "newStatus": "to research",
                "id": "POI-4220",
                "title": "cursor researching - Convert surplus inputs",
            }
        }

        self.assertIsNone(build_issue_title_update(event))

    def test_returns_none_without_issue_id_or_title(self):
        self.assertIsNone(
            build_issue_title_update(
                {
                    "triggerContext": {
                        "trigger": "status_changed",
                        "newStatus": "to research",
                        "title": "Convert surplus inputs",
                    }
                }
            )
        )
        self.assertIsNone(
            build_issue_title_update(
                {
                    "triggerContext": {
                        "trigger": "status_changed",
                        "newStatus": "to research",
                        "id": "POI-4220",
                    }
                }
            )
        )


if __name__ == "__main__":
    unittest.main()
