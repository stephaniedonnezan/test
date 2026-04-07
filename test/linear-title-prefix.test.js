const test = require("node:test");
const assert = require("node:assert/strict");

const {
  RESEARCH_PREFIX,
  buildIssueTitleForStatusChange,
} = require("../src/linear-title-prefix");

test("adds research prefix when status is to research", () => {
  const title = buildIssueTitleForStatusChange({
    title: "Add external connectors into the container logic",
    newStatus: "to research",
  });

  assert.equal(
    title,
    `${RESEARCH_PREFIX}: Add external connectors into the container logic`,
  );
});

test("adds research prefix case-insensitively for status", () => {
  const title = buildIssueTitleForStatusChange({
    title: "Investigate connector ingestion",
    newStatus: "To Research",
  });

  assert.equal(title, `${RESEARCH_PREFIX}: Investigate connector ingestion`);
});

test("does not change title for statuses other than to research", () => {
  const originalTitle = "Investigate connector ingestion";
  const title = buildIssueTitleForStatusChange({
    title: originalTitle,
    newStatus: "in review",
  });

  assert.equal(title, originalTitle);
});

test("does not duplicate the prefix", () => {
  const prefixedTitle = `${RESEARCH_PREFIX}: Investigate connector ingestion`;
  const title = buildIssueTitleForStatusChange({
    title: prefixedTitle,
    newStatus: "to research",
  });

  assert.equal(title, prefixedTitle);
});

test("throws when title is missing", () => {
  assert.throws(
    () => buildIssueTitleForStatusChange({ title: "", newStatus: "to research" }),
    /title must be a non-empty string/,
  );
});

