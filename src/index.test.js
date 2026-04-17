import test from "node:test";
import assert from "node:assert/strict";

import { handleIssueStatusChanged } from "./index.js";

test("handleIssueStatusChanged returns update payload for to research", () => {
  const action = handleIssueStatusChanged({
    triggerContext: {
      id: "POI-4468",
      newStatus: "to research",
      title: "Add delivery destination address to container events excel export + upload",
    },
  });

  assert.deepEqual(action, {
    action: "update_issue_title",
    issueId: "POI-4468",
    title: "Cursor researching: Add delivery destination address to container events excel export + upload",
  });
});

test("handleIssueStatusChanged returns null for non-matching statuses", () => {
  const action = handleIssueStatusChanged({
    triggerContext: {
      id: "POI-4468",
      newStatus: "in progress",
      title: "Add delivery destination address to container events excel export + upload",
    },
  });

  assert.equal(action, null);
});
