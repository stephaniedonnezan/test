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
    withResearchingPrefix("Do we need a frontend?"),
    `${RESEARCHING_TITLE_PREFIX}: Do we need a frontend?`,
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
      title: "Do we need a frontend?",
      id: "POI-4404",
    },
  };

  assert.deepEqual(buildIssueTitleUpdate(payload), {
    issueId: "POI-4404",
    previousTitle: "Do we need a frontend?",
    nextTitle: "Cursor researching: Do we need a frontend?",
  });
});

test("buildIssueTitleUpdate returns null when title already prefixed", () => {
  const payload = {
    triggerContext: {
      trigger: "status_changed",
      newStatus: "to research",
      title: "Cursor researching: Do we need a frontend?",
      id: "POI-4404",
    },
  };

  assert.equal(buildIssueTitleUpdate(payload), null);
});

test("buildIssueTitleUpdate returns null for unrelated status", () => {
  const payload = {
    triggerContext: {
      trigger: "status_changed",
      newStatus: "in progress",
      title: "Do we need a frontend?",
      id: "POI-4404",
    },
  };

  assert.equal(buildIssueTitleUpdate(payload), null);
});
