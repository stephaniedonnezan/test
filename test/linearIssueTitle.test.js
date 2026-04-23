const test = require("node:test");
const assert = require("node:assert/strict");
const {
  updateIssueTitleForStatusChange,
  isResearchStatus,
} = require("../src/linearIssueTitle");

test("recognizes to research status variants", () => {
  assert.equal(isResearchStatus("to research"), true);
  assert.equal(isResearchStatus("To Research"), true);
  assert.equal(isResearchStatus("to_research"), true);
  assert.equal(isResearchStatus("to-research"), true);
  assert.equal(isResearchStatus("in review"), false);
});

test('prefixes issue title when new status is "to research"', () => {
  const result = updateIssueTitleForStatusChange({
    title: "[Lhyfe] Issue to container initialisation 3-38-054",
    newStatus: "to research",
  });

  assert.equal(
    result,
    "Cursor researching - [Lhyfe] Issue to container initialisation 3-38-054",
  );
});

test("does not duplicate existing research prefix", () => {
  const result = updateIssueTitleForStatusChange({
    title: "Cursor researching - Existing title",
    newStatus: "to research",
  });

  assert.equal(result, "Cursor researching - Existing title");
});

test("keeps title unchanged for non-target statuses", () => {
  const result = updateIssueTitleForStatusChange({
    title: "Regular title",
    newStatus: "In Review",
  });

  assert.equal(result, "Regular title");
});
