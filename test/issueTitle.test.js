const test = require("node:test");
const assert = require("node:assert/strict");

const { updateIssueTitleForStatus } = require("../src/issueTitle");

test("adds prefix when status is to research", () => {
  assert.equal(
    updateIssueTitleForStatus({
      title: "Implementation",
      newStatus: "to research",
    }),
    "Cursor researching - Implementation",
  );
});

test("does not duplicate prefix when already present", () => {
  assert.equal(
    updateIssueTitleForStatus({
      title: "Cursor researching - Implementation",
      newStatus: "to research",
    }),
    "Cursor researching - Implementation",
  );
});

test("does not change title for other statuses", () => {
  assert.equal(
    updateIssueTitleForStatus({
      title: "Implementation",
      newStatus: "In Progress",
    }),
    "Implementation",
  );
});

test("handles mixed-case status values", () => {
  assert.equal(
    updateIssueTitleForStatus({
      title: "Implementation",
      newStatus: "To Research",
    }),
    "Cursor researching - Implementation",
  );
});
