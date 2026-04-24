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
    withResearchingPrefix("Wrong e_td for Delivery 7217"),
    `${RESEARCHING_TITLE_PREFIX}: Wrong e_td for Delivery 7217`,
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
      title: "Wrong e_td for Delivery 7217",
      id: "POI-4546",
    },
  };

  assert.deepEqual(buildIssueTitleUpdate(payload), {
    issueId: "POI-4546",
    previousTitle: "Wrong e_td for Delivery 7217",
    nextTitle: "Cursor researching: Wrong e_td for Delivery 7217",
  });
});

test("buildIssueTitleUpdate returns null when title already prefixed", () => {
  const payload = {
    triggerContext: {
      trigger: "status_changed",
      newStatus: "to research",
      title: "Cursor researching: Wrong e_td for Delivery 7217",
      id: "POI-4546",
    },
  };

  assert.equal(buildIssueTitleUpdate(payload), null);
});

test("buildIssueTitleUpdate returns null for unrelated status", () => {
  const payload = {
    triggerContext: {
      trigger: "status_changed",
      newStatus: "in review",
      title: "Wrong e_td for Delivery 7217",
      id: "POI-4546",
    },
  };

  assert.equal(buildIssueTitleUpdate(payload), null);
});
