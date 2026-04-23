const test = require("node:test");
const assert = require("node:assert/strict");

const {
  RESEARCHING_TITLE_PREFIX,
  buildIssueTitleUpdate,
  hasResearchingPrefix,
  shouldApplyResearchingPrefix,
  withResearchingPrefix,
} = require("../src/linearIssueTitleAutomation");

test("shouldApplyResearchingPrefix only returns true for status_changed to 'to research'", () => {
  assert.equal(
    shouldApplyResearchingPrefix({
      trigger: "status_changed",
      newStatus: "to research",
    }),
    true,
  );

  assert.equal(
    shouldApplyResearchingPrefix({
      trigger: "status_changed",
      newStatus: "To Research",
    }),
    true,
  );

  assert.equal(
    shouldApplyResearchingPrefix({
      trigger: "created",
      newStatus: "to research",
    }),
    false,
  );

  assert.equal(
    shouldApplyResearchingPrefix({
      trigger: "status_changed",
      newStatus: "in progress",
    }),
    false,
  );
});

test("withResearchingPrefix adds prefix and stays idempotent", () => {
  assert.equal(
    withResearchingPrefix("Delete the S3 pos file after the transaction completes"),
    `${RESEARCHING_TITLE_PREFIX}: Delete the S3 pos file after the transaction completes`,
  );

  assert.equal(
    withResearchingPrefix("Cursor researching: Existing"),
    "Cursor researching: Existing",
  );
});

test("hasResearchingPrefix handles case-insensitive values", () => {
  assert.equal(hasResearchingPrefix("cursor researching: test"), true);
  assert.equal(hasResearchingPrefix("Cursor researching test"), true);
  assert.equal(hasResearchingPrefix("Researching cursor test"), false);
});

test("buildIssueTitleUpdate returns update payload for matching event", () => {
  const payload = {
    triggerContext: {
      trigger: "status_changed",
      newStatus: "to research",
      title: "Delete the S3 pos file after the transaction completes",
      id: "POI-4511",
    },
  };

  assert.deepEqual(buildIssueTitleUpdate(payload), {
    issueId: "POI-4511",
    previousTitle: "Delete the S3 pos file after the transaction completes",
    nextTitle:
      "Cursor researching: Delete the S3 pos file after the transaction completes",
  });
});

test("buildIssueTitleUpdate returns null when title already prefixed", () => {
  const payload = {
    triggerContext: {
      trigger: "status_changed",
      newStatus: "to research",
      title: "Cursor researching: Delete the S3 pos file after the transaction completes",
      id: "POI-4511",
    },
  };

  assert.equal(buildIssueTitleUpdate(payload), null);
});

test("buildIssueTitleUpdate returns null for unrelated status", () => {
  const payload = {
    triggerContext: {
      trigger: "status_changed",
      newStatus: "in progress",
      title: "Delete the S3 pos file after the transaction completes",
      id: "POI-4511",
    },
  };

  assert.equal(buildIssueTitleUpdate(payload), null);
});
