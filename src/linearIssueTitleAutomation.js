"use strict";

const RESEARCH_STATUS = "to research";
const RESEARCHING_TITLE_PREFIX = "Cursor researching";

function normalizeStatus(value) {
  return String(value ?? "")
    .trim()
    .replace(/[-_]+/g, " ")
    .replace(/\s+/g, " ")
    .toLowerCase();
}

function normalizeTrigger(value) {
  return String(value ?? "")
    .trim()
    .replace(/[-\s]+/g, "_")
    .toLowerCase();
}

function getTriggerContext(event) {
  return event?.triggerContext ?? event ?? {};
}

function hasResearchingPrefix(title) {
  return /^\s*cursor researching\b/i.test(String(title ?? ""));
}

function shouldApplyResearchingPrefix(event) {
  const triggerContext = getTriggerContext(event);
  const trigger = normalizeTrigger(
    triggerContext.trigger ?? triggerContext.webhookType ?? triggerContext.type,
  );

  if (trigger !== "status_changed") {
    return false;
  }

  return (
    normalizeStatus(triggerContext.newStatus ?? triggerContext.status) ===
    RESEARCH_STATUS
  );
}

function withResearchingPrefix(title) {
  const cleanTitle = String(title ?? "").trim();

  if (!cleanTitle) {
    return RESEARCHING_TITLE_PREFIX;
  }

  if (hasResearchingPrefix(cleanTitle)) {
    return cleanTitle;
  }

  return `${RESEARCHING_TITLE_PREFIX}: ${cleanTitle}`;
}

function buildIssueTitleUpdate(event) {
  const triggerContext = getTriggerContext(event);

  if (!shouldApplyResearchingPrefix(event)) {
    return null;
  }

  const previousTitle = String(triggerContext.title ?? "");
  const nextTitle = withResearchingPrefix(previousTitle);

  if (nextTitle === previousTitle) {
    return null;
  }

  return {
    action: "update_issue_title",
    issueId: triggerContext.id,
    issueUrl: triggerContext.url,
    previousTitle,
    title: nextTitle,
  };
}

module.exports = {
  RESEARCH_STATUS,
  RESEARCHING_TITLE_PREFIX,
  buildIssueTitleUpdate,
  getTriggerContext,
  hasResearchingPrefix,
  normalizeStatus,
  normalizeTrigger,
  shouldApplyResearchingPrefix,
  withResearchingPrefix,
};
