const { buildIssueTitleUpdate } = require("./linearIssueTitleAutomation");

/**
 * Entrypoint for Linear issue status change automation.
 * Returns a declarative update payload for caller-side API execution.
 */
function handleIssueStatusChanged(event = {}) {
  const update = buildIssueTitleUpdate(event);
  if (!update) {
    return null;
  }

  return {
    action: "update_issue_title",
    issueId: update.issueId,
    title: update.nextTitle,
    previousTitle: update.previousTitle,
  };
}

module.exports = {
  handleAutomationEvent: handleIssueStatusChanged,
  handleIssueStatusChanged,
};
