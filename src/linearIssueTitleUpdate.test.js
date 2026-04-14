const test = require("node:test");
const assert = require("node:assert/strict");

const {
  RESEARCHING_MARKER,
  addResearchingMarkerToTitle,
  getUpdatedIssueTitle,
  getUpdatedTitleFromLinearAutomationPayload,
} = require("./linearIssueTitleUpdate");

test("adds marker when status changes to to research", () => {
  const updatedTitle = getUpdatedIssueTitle({
    title: "Update the generic fullscreen dialogs styles",
    newStatus: "to research",
  });

  assert.equal(
    updatedTitle,
    `${RESEARCHING_MARKER} - Update the generic fullscreen dialogs styles`,
  );
});

test("does not add marker when status is not to research", () => {
  const title = "Update the generic fullscreen dialogs styles";
  const updatedTitle = getUpdatedIssueTitle({
    title,
    newStatus: "QA UX/UI",
  });

  assert.equal(updatedTitle, title);
});

test("status matching is case-insensitive and trims spaces", () => {
  const updatedTitle = getUpdatedIssueTitle({
    title: "Fix flaky modal layout",
    newStatus: "  TO RESEARCH  ",
  });

  assert.equal(updatedTitle, `${RESEARCHING_MARKER} - Fix flaky modal layout`);
});

test("does not duplicate marker when title already includes it", () => {
  const title = "Cursor researching - Fix flaky modal layout";
  const updatedTitle = getUpdatedIssueTitle({
    title,
    newStatus: "to research",
  });

  assert.equal(updatedTitle, title);
});

test("returns marker only when title is empty", () => {
  assert.equal(addResearchingMarkerToTitle(""), RESEARCHING_MARKER);
});

test("reads triggerContext payload from Linear automation event", () => {
  const updatedTitle = getUpdatedTitleFromLinearAutomationPayload({
    triggerContext: {
      title: "Add new API key dialog spacing fix",
      newStatus: "to research",
    },
  });

  assert.equal(
    updatedTitle,
    `${RESEARCHING_MARKER} - Add new API key dialog spacing fix`,
  );
});
