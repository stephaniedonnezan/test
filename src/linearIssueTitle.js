const RESEARCH_PREFIX = "Cursor researching";
const STATUS_CHANGED_TRIGGER = "status_changed";
const TARGET_STATUS = "to research";

function normalize(value) {
  return String(value ?? "").trim().toLowerCase();
}

export function hasResearchPrefix(title) {
  const normalizedTitle = normalize(title);
  return normalizedTitle.startsWith(normalize(RESEARCH_PREFIX));
}

export function buildResearchTitle(title) {
  const trimmedTitle = String(title ?? "").trim();
  if (!trimmedTitle) {
    return RESEARCH_PREFIX;
  }

  if (hasResearchPrefix(trimmedTitle)) {
    return trimmedTitle;
  }

  return `${RESEARCH_PREFIX}: ${trimmedTitle}`;
}

export function getUpdatedIssueTitle(triggerContext = {}) {
  const trigger = normalize(triggerContext.trigger);
  const newStatus = normalize(triggerContext.newStatus);

  if (trigger !== STATUS_CHANGED_TRIGGER || newStatus !== TARGET_STATUS) {
    return null;
  }

  return buildResearchTitle(triggerContext.title);
}

export { RESEARCH_PREFIX };
