const RESEARCH_STATUS = "to research";
const RESEARCHING_TITLE_PREFIX = "Cursor researching";

function normalize(value) {
  return String(value ?? "").trim().toLowerCase();
}

function shouldApplyResearchingPrefix(triggerContext) {
  if (!triggerContext || triggerContext.trigger !== "status_changed") {
    return false;
  }

  return normalize(triggerContext.newStatus) === RESEARCH_STATUS;
}

function hasResearchingPrefix(title) {
  return /^\s*cursor researching\b/i.test(String(title ?? ""));
}

function withResearchingPrefix(title) {
  const cleanedTitle = String(title ?? "").trim();
  if (!cleanedTitle) {
    return RESEARCHING_TITLE_PREFIX;
  }

  if (hasResearchingPrefix(cleanedTitle)) {
    return cleanedTitle;
  }

  return `${RESEARCHING_TITLE_PREFIX}: ${cleanedTitle}`;
}

function buildIssueTitleUpdate(payload) {
  const triggerContext = payload?.triggerContext;
  if (!shouldApplyResearchingPrefix(triggerContext)) {
    return null;
  }

  const currentTitle = String(triggerContext?.title ?? "");
  const nextTitle = withResearchingPrefix(currentTitle);

  if (nextTitle === currentTitle) {
    return null;
  }

  return {
    issueId: triggerContext.id,
    previousTitle: currentTitle,
    nextTitle,
  };
}

module.exports = {
  RESEARCH_STATUS,
  RESEARCHING_TITLE_PREFIX,
  buildIssueTitleUpdate,
  hasResearchingPrefix,
  shouldApplyResearchingPrefix,
  withResearchingPrefix,
};
