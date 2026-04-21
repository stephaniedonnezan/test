const test = require("node:test");
const assert = require("node:assert/strict");

const {
  CURSOR_RESEARCHING_PREFIX,
  applyCursorResearchingTitleToAutomationPayload,
  updateIssueTitleForResearchStatus,
} = require("../src/linearTitleUpdater");

test("adds prefix when status changes to to research", () => {
  const title = updateIssueTitleForResearchStatus({
    trigger: "status_changed",
    newStatus: "to research",
    title: "Allow dispatchDestinationAddress to be optional",
  });

  assert.equal(
    title,
    "Cursor researching: Allow dispatchDestinationAddress to be optional",
  );
});

test("does not modify title when trigger is not status_changed", () => {
  const originalTitle = "Some issue";
  const title = updateIssueTitleForResearchStatus({
    trigger: "created",
    newStatus: "to research",
    title: originalTitle,
  });

  assert.equal(title, originalTitle);
});

test("does not modify title when status is not to research", () => {
  const originalTitle = "Some issue";
  const title = updateIssueTitleForResearchStatus({
    trigger: "status_changed",
    newStatus: "in progress",
    title: originalTitle,
  });

  assert.equal(title, originalTitle);
});

test("does not duplicate prefix when already present (case-insensitive)", () => {
  const originalTitle = "cursor researching: Investigate API drift";
  const title = updateIssueTitleForResearchStatus({
    trigger: "status_changed",
    newStatus: "to research",
    title: originalTitle,
  });

  assert.equal(title, originalTitle);
});

test("payload helper updates nested triggerContext title", () => {
  const input = {
    triggerType: "linear",
    triggerContext: {
      trigger: "status_changed",
      newStatus: "to research",
      title: "Investigate background job failures",
    },
  };

  const output = applyCursorResearchingTitleToAutomationPayload(input);
  assert.equal(
    output.triggerContext.title,
    `${CURSOR_RESEARCHING_PREFIX}: Investigate background job failures`,
  );
});

test("payload helper returns original payload when no changes needed", () => {
  const input = {
    triggerType: "linear",
    triggerContext: {
      trigger: "status_changed",
      newStatus: "in progress",
      title: "No mutation expected",
    },
  };

  const output = applyCursorResearchingTitleToAutomationPayload(input);
  assert.equal(output, input);
});
