"use strict";

const test = require("node:test");
const assert = require("node:assert/strict");

const { handleAutomationEvent, handleIssueStatusChanged } = require("../src");

test("handleIssueStatusChanged returns update payload for to research", () => {
  const action = handleIssueStatusChanged({
    triggerContext: {
      trigger: "status_changed",
      id: "POI-4206",
      newStatus: "to research",
      title: "[][Dev] - PoS document handling",
    },
  });

  assert.deepEqual(action, {
    action: "update_issue_title",
    issueId: "POI-4206",
    issueUrl: undefined,
    previousTitle: "[][Dev] - PoS document handling",
    title: "Cursor researching: [][Dev] - PoS document handling",
  });
});

test("handleIssueStatusChanged returns null for non matching status", () => {
  const action = handleIssueStatusChanged({
    triggerContext: {
      trigger: "status_changed",
      id: "POI-4206",
      newStatus: "Done",
      title: "[][Dev] - PoS document handling",
    },
  });

  assert.equal(action, null);
});

test("handleAutomationEvent aliases the status change handler", () => {
  assert.equal(handleAutomationEvent, handleIssueStatusChanged);
});
