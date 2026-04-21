import unittest

from linear_title_prefix import (
    DEFAULT_PREFIX,
    _build_prefixed_title,
    build_issue_title_update,
)


def _event(**trigger_context):
    return {"triggerContext": trigger_context}


class BuildIssueTitleUpdateTests(unittest.TestCase):
    def test_returns_update_for_status_change_to_research(self):
        event = _event(
            trigger="status_changed",
            newStatus="to research",
            title="Update initialisation of qualified output entities",
            id="POI-4511",
        )

        result = build_issue_title_update(event)

        self.assertEqual(
            {
                "action": "update_issue_title",
                "issueId": "POI-4511",
                "title": f"{DEFAULT_PREFIX}: "
                "Update initialisation of qualified output entities",
            },
            result,
        )

    def test_returns_none_when_not_status_change(self):
        event = _event(
            trigger="comment_created",
            newStatus="to research",
            title="My issue",
            id="POI-1",
        )
        self.assertIsNone(build_issue_title_update(event))

    def test_returns_none_when_new_status_not_research(self):
        event = _event(
            trigger="status_changed",
            newStatus="In Progress",
            title="My issue",
            id="POI-2",
        )
        self.assertIsNone(build_issue_title_update(event))

    def test_falls_back_to_status_when_new_status_missing(self):
        event = _event(
            trigger="status_changed",
            status="to research",
            title="My issue",
            id="POI-3",
        )

        result = build_issue_title_update(event)
        self.assertEqual("POI-3", result["issueId"])
        self.assertEqual(f"{DEFAULT_PREFIX}: My issue", result["title"])

    def test_status_and_trigger_normalization(self):
        event = _event(
            trigger="STATUS-CHANGED",
            newStatus=" To   Research ",
            title="My issue",
            id="POI-4",
        )

        result = build_issue_title_update(event)
        self.assertIsNotNone(result)
        self.assertEqual(f"{DEFAULT_PREFIX}: My issue", result["title"])

    def test_returns_none_when_prefix_already_present(self):
        event = _event(
            trigger="status_changed",
            newStatus="to research",
            title="cursor researching: My issue",
            id="POI-5",
        )
        self.assertIsNone(build_issue_title_update(event))

    def test_returns_none_without_title(self):
        event = _event(
            trigger="status_changed",
            newStatus="to research",
            id="POI-6",
        )
        self.assertIsNone(build_issue_title_update(event))

    def test_returns_none_without_issue_id(self):
        event = _event(
            trigger="status_changed",
            newStatus="to research",
            title="My issue",
        )
        self.assertIsNone(build_issue_title_update(event))


class BuildPrefixedTitleTests(unittest.TestCase):
    def test_empty_title_returns_prefix(self):
        self.assertEqual(DEFAULT_PREFIX, _build_prefixed_title("", DEFAULT_PREFIX))

    def test_existing_prefix_not_duplicated(self):
        self.assertEqual(
            "Cursor researching: Existing",
            _build_prefixed_title("Cursor researching: Existing", DEFAULT_PREFIX),
        )

    def test_non_prefixed_title_gets_prefix(self):
        self.assertEqual(
            "Cursor researching: Existing",
            _build_prefixed_title("Existing", DEFAULT_PREFIX),
        )


if __name__ == "__main__":
    unittest.main()
