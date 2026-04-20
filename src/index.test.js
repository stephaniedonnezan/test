import test from "node:test";
import assert from "node:assert/strict";

import { handleIssueStatusChanged } from "./index.js";

test("handleIssueStatusChanged returns update payload for to research", () => {
  const action = handleIssueStatusChanged({
    triggerContext: {
      trigger: "status_changed",
      id: "POI-4506",
      newStatus: "to research",
      title: "QA Value edition: shouldn't trigger the BOP ?",
    },
  });

  assert.deepEqual(action, {
    action: "update_issue_title",
    issueId: "POI-4506",
    title: "Cursor researching: QA Value edition: shouldn't trigger the BOP ?",
  });
});

test("handleIssueStatusChanged returns null for non-matching statuses", () => {
  const action = handleIssueStatusChanged({
    triggerContext: {
      trigger: "status_changed",
      id: "POI-4506",
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
      id: "POI-4506",
      newStatus: "to research",
      title: "Some title",
    },
  });

  assert.equal(action, null);
});
