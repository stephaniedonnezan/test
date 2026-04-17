import test from "node:test";
import assert from "node:assert/strict";

import { handleIssueStatusChanged } from "./index.js";

test("handleIssueStatusChanged returns update payload for to research", () => {
  const action = handleIssueStatusChanged({
    triggerContext: {
      id: "POI-4466",
      newStatus: "to research",
      title: "Container Mass Balance view improvements",
    },
  });

  assert.deepEqual(action, {
    action: "update_issue_title",
    issueId: "POI-4466",
    title: "Cursor researching: Container Mass Balance view improvements",
  });
});

test("handleIssueStatusChanged returns null for non-matching statuses", () => {
  const action = handleIssueStatusChanged({
    triggerContext: {
      id: "POI-4466",
      newStatus: "in progress",
      title: "Container Mass Balance view improvements",
    },
  });

  assert.equal(action, null);
});
