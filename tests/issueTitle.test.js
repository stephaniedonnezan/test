const test = require("node:test");
const assert = require("node:assert/strict");

const {
  shouldApplyResearchTag,
  addResearchTagToTitle,
  updateIssueTitleOnStatusChange,
} = require("../automation/issueTitle");

test("shouldApplyResearchTag only matches to research (case-insensitive)", () => {
  assert.equal(shouldApplyResearchTag("to research"), true);
  assert.equal(shouldApplyResearchTag("To Research"), true);
  assert.equal(shouldApplyResearchTag("in review"), false);
  assert.equal(shouldApplyResearchTag(""), false);
  assert.equal(shouldApplyResearchTag(null), false);
});

test("addResearchTagToTitle appends tag when missing", () => {
  assert.equal(
    addResearchTagToTitle(
      "Lhyfe Deployment: Take surpluses of September and convert them to qualified inputs into the container logic",
    ),
    "Lhyfe Deployment: Take surpluses of September and convert them to qualified inputs into the container logic Cursor researching",
  );
});

test("addResearchTagToTitle avoids duplicate tag", () => {
  assert.equal(
    addResearchTagToTitle(
      "Lhyfe Deployment: Take surpluses of September and convert them to qualified inputs into the container logic Cursor researching",
    ),
    "Lhyfe Deployment: Take surpluses of September and convert them to qualified inputs into the container logic Cursor researching",
  );
});

test("updateIssueTitleOnStatusChange returns unchanged title for non-target statuses", () => {
  const result = updateIssueTitleOnStatusChange({
    triggerContext: {
      newStatus: "In Review",
      title: "Issue title",
    },
  });

  assert.equal(result, "Issue title");
});

test("updateIssueTitleOnStatusChange appends tag for to research status", () => {
  const result = updateIssueTitleOnStatusChange({
    triggerContext: {
      newStatus: "to research",
      title: "Issue title",
    },
  });

  assert.equal(result, "Issue title Cursor researching");
});

