const test = require("node:test");
const assert = require("node:assert/strict");

const { handleIssueStatusChanged } = require("../src/index");

test("handleIssueStatusChanged returns update payload for to research", () => {
  const action = handleIssueStatusChanged({
    triggerContext: {
      trigger: "status_changed",
      id: "POI-4240",
      newStatus: "to research",
      title: "WP1: Audit Overview & Management",
    },
  });

  assert.deepEqual(action, {
    action: "update_issue_title",
    issueId: "POI-4240",
    title: "Cursor researching: WP1: Audit Overview & Management",
    previousTitle: "WP1: Audit Overview & Management",
  });
});

test("handleIssueStatusChanged returns null for non matching status", () => {
  const action = handleIssueStatusChanged({
    triggerContext: {
      trigger: "status_changed",
      id: "POI-4240",
      newStatus: "in progress",
      title: "WP1: Audit Overview & Management",
    },
  });

  assert.equal(action, null);
});
