const test = require("node:test");
const assert = require("node:assert/strict");

const {
  buildUpdatedIssueTitleFromStatusChangePayload,
} = require("../src/handleLinearIssueStatusChange");

test("returns unchanged title when triggerContext status is not to research", () => {
  const payload = {
    triggerContext: {
      title: "Implementation",
      newStatus: "In Progress",
    },
  };

  const result = buildUpdatedIssueTitleFromStatusChangePayload(payload);
  assert.equal(result, "Implementation");
});

test("adds Cursor researching when triggerContext status is to research", () => {
  const payload = {
    triggerContext: {
      title: "Implementation",
      newStatus: "to research",
    },
  };

  const result = buildUpdatedIssueTitleFromStatusChangePayload(payload);
  assert.equal(result, "Cursor researching - Implementation");
});

test("avoids duplicate tag when title already contains Cursor researching", () => {
  const payload = {
    triggerContext: {
      title: "Cursor researching - Implementation",
      newStatus: "to research",
    },
  };

  const result = buildUpdatedIssueTitleFromStatusChangePayload(payload);
  assert.equal(result, "Cursor researching - Implementation");
});

test("falls back to status when newStatus is missing", () => {
  const payload = {
    triggerContext: {
      title: "Implementation",
      status: "To Research",
    },
  };

  const result = buildUpdatedIssueTitleFromStatusChangePayload(payload);
  assert.equal(result, "Cursor researching - Implementation");
});
