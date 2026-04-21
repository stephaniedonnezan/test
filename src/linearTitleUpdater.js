const CURSOR_RESEARCHING_PREFIX = "Cursor researching";
const CURSOR_RESEARCHING_PREFIX_PATTERN = /^cursor researching\b/i;

/**
 * Returns an updated issue title for a Linear status-change trigger.
 * If status changed to "to research", prefixes title with "Cursor researching"
 * unless already present.
 *
 * @param {object} triggerPayload
 * @param {string} triggerPayload.trigger
 * @param {string} triggerPayload.newStatus
 * @param {string} triggerPayload.title
 * @returns {string}
 */
function updateIssueTitleForResearchStatus(triggerPayload) {
  const payload = triggerPayload || {};
  const trigger = (payload.trigger || "").trim().toLowerCase();
  const newStatus = (payload.newStatus || "").trim().toLowerCase();
  const title = payload.title || "";

  if (trigger !== "status_changed") {
    return title;
  }

  if (newStatus !== "to research") {
    return title;
  }

  if (CURSOR_RESEARCHING_PREFIX_PATTERN.test(title.trim())) {
    return title;
  }

  return title ? `${CURSOR_RESEARCHING_PREFIX}: ${title}` : CURSOR_RESEARCHING_PREFIX;
}

/**
 * Updates automation payload triggerContext.title if issue moved to "to research".
 *
 * @param {object} automationPayload
 * @returns {object}
 */
function applyCursorResearchingTitleToAutomationPayload(automationPayload) {
  const payload = automationPayload || {};
  const triggerContext = payload.triggerContext || {};
  const nextTitle = updateIssueTitleForResearchStatus({
    trigger: triggerContext.trigger,
    newStatus: triggerContext.newStatus,
    title: triggerContext.title,
  });

  if (nextTitle === (triggerContext.title || "")) {
    return payload;
  }

  return {
    ...payload,
    triggerContext: {
      ...triggerContext,
      title: nextTitle,
    },
  };
}

module.exports = {
  CURSOR_RESEARCHING_PREFIX,
  CURSOR_RESEARCHING_PREFIX_PATTERN,
  applyCursorResearchingTitleToAutomationPayload,
  updateIssueTitleForResearchStatus,
};
