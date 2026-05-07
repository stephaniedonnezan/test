"use strict";

const { buildIssueTitleUpdate } = require("./linearIssueTitleAutomation");

function handleIssueStatusChanged(event = {}) {
  return buildIssueTitleUpdate(event);
}

module.exports = {
  handleAutomationEvent: handleIssueStatusChanged,
  handleIssueStatusChanged,
};
