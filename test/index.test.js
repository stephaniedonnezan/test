import test from "node:test";
import assert from "node:assert/strict";

import { handleIssueStatusChanged } from "../src/index.js";

test("handleIssueStatusChanged returns update payload for to research", () => {
  const action = handleIssueStatusChanged({
    triggerContext: {
      id: "POI-4472",
      trigger: "status_changed",
      newStatus: "to research",
      title: "Excel download button styling",
    },
  });

  assert.deepEqual(action, {
    action: "update_issue_title",
    issueId: "POI-4472",
    title: "Cursor researching: Excel download button styling",
  });
});

test("handleIssueStatusChanged returns null for non-matching events", () => {
  const action = handleIssueStatusChanged({
    triggerContext: {
      id: "POI-4472",
      trigger: "status_changed",
      newStatus: "DEV",
      title: "Excel download button styling",
    },
  });

  assert.equal(action, null);
});
