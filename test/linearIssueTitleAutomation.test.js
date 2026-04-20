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
    withResearchingPrefix("Agile Ticket Methodologies to try"),
    `${RESEARCHING_TITLE_PREFIX}: Agile Ticket Methodologies to try`,
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
      title: "Agile Ticket Methodologies to try",
      id: "POI-4492",
    },
  };

  assert.deepEqual(buildIssueTitleUpdate(payload), {
    issueId: "POI-4492",
    previousTitle: "Agile Ticket Methodologies to try",
    nextTitle: "Cursor researching: Agile Ticket Methodologies to try",
  });
});

test("buildIssueTitleUpdate returns null when title already prefixed", () => {
  const payload = {
    triggerContext: {
      trigger: "status_changed",
      newStatus: "to research",
      title: "Cursor researching: Agile Ticket Methodologies to try",
      id: "POI-4492",
    },
  };

  assert.equal(buildIssueTitleUpdate(payload), null);
});

test("buildIssueTitleUpdate returns null for unrelated status", () => {
  const payload = {
    triggerContext: {
      trigger: "status_changed",
      newStatus: "in progress",
      title: "Agile Ticket Methodologies to try",
      id: "POI-4492",
    },
  };

  assert.equal(buildIssueTitleUpdate(payload), null);
});
