import test from "node:test";
import assert from "node:assert/strict";

import { handleIssueStatusChanged } from "./index.js";

test("handleIssueStatusChanged returns update payload for to research", () => {
  const action = handleIssueStatusChanged({
    triggerContext: {
      trigger: "status_changed",
      id: "POI-4179",
      newStatus: "to research",
      title: "Add Info Snack Bar informing user of new release notes at new login",
    },
  });

  assert.deepEqual(action, {
    action: "update_issue_title",
    issueId: "POI-4179",
    title:
      "Cursor researching: Add Info Snack Bar informing user of new release notes at new login",
  });
});

test("handleIssueStatusChanged returns null for non-matching statuses", () => {
  const action = handleIssueStatusChanged({
    triggerContext: {
      trigger: "status_changed",
      id: "POI-4179",
      newStatus: "in progress",
      title: "Some title",
    },
  });

  assert.equal(action, null);
});

test("handleIssueStatusChanged returns null for non-status trigger", () => {
  const action = handleIssueStatusChanged({
    triggerContext: {
      trigger: "comment_added",
      id: "POI-4179",
      newStatus: "to research",
      title: "Some title",
    },
  });

  assert.equal(action, null);
});
