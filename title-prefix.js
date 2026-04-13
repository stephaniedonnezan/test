const RESEARCHING_PREFIX = "Cursor researching";

function normalizeStatus(status) {
  return String(status ?? "")
    .trim()
    .toLowerCase()
    .replace(/\s+/g, " ");
}

function normalizeToken(value) {
  return String(value ?? "").trim().toLowerCase();
}

function hasResearchingPrefix(title) {
  const normalizedTitle = String(title ?? "").trim();
  const prefixPattern = new RegExp(`^${RESEARCHING_PREFIX}(\\b|\\s*[:\\-|])`, "i");
  return prefixPattern.test(normalizedTitle) || normalizedTitle.toLowerCase() === RESEARCHING_PREFIX.toLowerCase();
}

function buildResearchingTitle(title) {
  const safeTitle = String(title ?? "").trim();
  if (safeTitle.length === 0) {
    return RESEARCHING_PREFIX;
  }

  if (hasResearchingPrefix(safeTitle)) {
    return safeTitle;
  }

  return `${RESEARCHING_PREFIX}: ${safeTitle}`;
}

function getUpdatedTitleForStatusChange(event) {
  const status = normalizeStatus(event?.newStatus);
  const title = String(event?.title ?? "");

  if (status !== "to research") {
    return {
      shouldUpdate: false,
      title,
    };
  }

  const updatedTitle = buildResearchingTitle(title);

  return {
    shouldUpdate: updatedTitle !== title,
    title: updatedTitle,
  };
}

function getIssueTitleUpdateFromAutomationEvent(payload) {
  const context = payload?.triggerContext ?? payload;
  const trigger = normalizeToken(context?.trigger);
  const webhookType = normalizeToken(context?.webhookType);

  if (trigger !== "status_changed" || webhookType !== "issue") {
    return {
      shouldUpdate: false,
      title: String(context?.title ?? ""),
    };
  }

  return getUpdatedTitleForStatusChange(context);
}

module.exports = {
  RESEARCHING_PREFIX,
  normalizeStatus,
  normalizeToken,
  hasResearchingPrefix,
  buildResearchingTitle,
  getUpdatedTitleForStatusChange,
  getIssueTitleUpdateFromAutomationEvent,
};
