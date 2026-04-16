function shouldApplyResearchTag(status) {
  return typeof status === "string" && status.trim().toLowerCase() === "to research";
}

function addResearchTagToTitle(title) {
  const safeTitle = typeof title === "string" ? title : "";
  const tag = "Cursor researching";
  if (safeTitle.includes(tag)) {
    return safeTitle;
  }
  return `${safeTitle} ${tag}`.trim();
}

function updateIssueTitleOnStatusChange(payload) {
  const safePayload = payload && typeof payload === "object" ? payload : {};
  const triggerContext =
    safePayload.triggerContext && typeof safePayload.triggerContext === "object"
      ? safePayload.triggerContext
      : {};
  const status = triggerContext.newStatus || triggerContext.status;
  const currentTitle = triggerContext.title;

  if (!shouldApplyResearchTag(status)) {
    return currentTitle;
  }

  return addResearchTagToTitle(currentTitle);
}

module.exports = {
  shouldApplyResearchTag,
  addResearchTagToTitle,
  updateIssueTitleOnStatusChange,
};
