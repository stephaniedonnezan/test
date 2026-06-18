'use strict';

const CURSOR_RESEARCHING_MARKER = 'Cursor researching';
const TO_RESEARCH_STATUS = 'to research';

function normalizeStatus(status) {
  return String(status || '')
    .trim()
    .replace(/\s+/g, ' ')
    .toLowerCase();
}

function isToResearchStatus(status) {
  return normalizeStatus(status) === TO_RESEARCH_STATUS;
}

function hasCursorResearchingMarker(title) {
  return new RegExp(`\\b${CURSOR_RESEARCHING_MARKER}\\b`, 'i').test(String(title || ''));
}

function addCursorResearchingToTitle(title) {
  const currentTitle = String(title || '').trim();

  if (hasCursorResearchingMarker(currentTitle)) {
    return currentTitle;
  }

  return currentTitle
    ? `${CURSOR_RESEARCHING_MARKER}: ${currentTitle}`
    : CURSOR_RESEARCHING_MARKER;
}

function isIssueStatusChangedEvent(triggerContext) {
  return (
    triggerContext &&
    triggerContext.triggerType === 'linear' &&
    triggerContext.webhookType === 'issue' &&
    triggerContext.trigger === 'status_changed'
  );
}

async function handleIssueStatusChangedToResearch(triggerContext, linearClient) {
  if (!isIssueStatusChangedEvent(triggerContext)) {
    return { updated: false, reason: 'ignored_event' };
  }

  const newStatus = triggerContext.newStatus || triggerContext.status;
  if (!isToResearchStatus(newStatus)) {
    return { updated: false, reason: 'ignored_status' };
  }

  if (!triggerContext.id) {
    throw new Error('Cannot update Linear issue title without an issue id.');
  }

  if (!linearClient || typeof linearClient.updateIssueTitle !== 'function') {
    throw new Error('A Linear client with updateIssueTitle(issueId, title) is required.');
  }

  const currentTitle = triggerContext.title || '';
  const nextTitle = addCursorResearchingToTitle(currentTitle);

  if (nextTitle === String(currentTitle || '').trim()) {
    return { updated: false, reason: 'already_marked', title: nextTitle };
  }

  await linearClient.updateIssueTitle(triggerContext.id, nextTitle);

  return { updated: true, issueId: triggerContext.id, title: nextTitle };
}

module.exports = {
  CURSOR_RESEARCHING_MARKER,
  addCursorResearchingToTitle,
  handleIssueStatusChangedToResearch,
  hasCursorResearchingMarker,
  isToResearchStatus,
  normalizeStatus
};
