const RESEARCH_PREFIX = 'Cursor researching';
const TARGET_STATUS = 'to research';

const STATUS_CHANGE_MARKERS = new Set(['status changed', 'status change', 'statuschanged']);
const ISSUE_UPDATE_MARKERS = new Set(['issue updated', 'updated issue', 'update', 'updated']);
const STATUS_FIELD_NAMES = new Set(['status', 'state', 'workflow state', 'workflowstate']);

function normalizeText(value) {
  if (value === null || value === undefined) {
    return '';
  }

  return String(value)
    .replace(/([a-z0-9])([A-Z])/g, '$1 $2')
    .replace(/[_-]+/g, ' ')
    .replace(/\s+/g, ' ')
    .trim()
    .toLowerCase();
}

function normalizeStatusName(statusName) {
  return normalizeText(statusName);
}

function statusNameFrom(value) {
  if (typeof value === 'string') {
    return value;
  }

  if (!value || typeof value !== 'object') {
    return '';
  }

  return (
    value.name ||
    value.status ||
    value.state?.name ||
    value.workflowState?.name ||
    value.workflow_state?.name ||
    ''
  );
}

function getPath(source, path) {
  return path.reduce((current, key) => {
    if (!current || typeof current !== 'object') {
      return undefined;
    }
    return current[key];
  }, source);
}

function firstStatus(source, paths) {
  for (const path of paths) {
    const status = statusNameFrom(getPath(source, path));
    if (status) {
      return status;
    }
  }
  return '';
}

function firstString(source, paths) {
  for (const path of paths) {
    const value = getPath(source, path);
    if (typeof value === 'string' && value.trim()) {
      return value.trim();
    }
  }
  return '';
}

function listIncludesStatusField(values) {
  if (!Array.isArray(values)) {
    return false;
  }

  return values.some((value) => STATUS_FIELD_NAMES.has(normalizeText(value)));
}

function hasStatusChangeMarker(payload) {
  const triggerValues = [
    payload?.triggerContext?.trigger,
    payload?.triggerContext?.webhookType,
    payload?.trigger,
    payload?.webhookType,
    payload?.type,
    payload?.action,
  ];

  if (triggerValues.some((value) => STATUS_CHANGE_MARKERS.has(normalizeText(value)))) {
    return true;
  }

  const actionValues = [payload?.action, payload?.triggerContext?.action];
  const isIssueUpdate = actionValues.some((value) => ISSUE_UPDATE_MARKERS.has(normalizeText(value)));
  if (!isIssueUpdate) {
    return false;
  }

  return (
    listIncludesStatusField(payload?.updatedFields) ||
    listIncludesStatusField(payload?.data?.updatedFields) ||
    listIncludesStatusField(payload?.triggerContext?.updatedFields) ||
    Boolean(payload?.data?.previous?.state || payload?.data?.previous?.status)
  );
}

function changedToResearch(payload) {
  const changedTo = normalizeStatusName(
    firstStatus(payload, [
      ['triggerContext', 'newStatus'],
      ['triggerContext', 'new_status'],
      ['triggerContext', 'status'],
      ['triggerContext', 'state'],
      ['triggerContext', 'workflowState'],
      ['newStatus'],
      ['new_status'],
      ['changedTo'],
      ['toStatus'],
      ['status'],
      ['state'],
      ['workflowState'],
      ['data', 'state'],
      ['data', 'status'],
      ['data', 'workflowState'],
      ['data', 'issue', 'state'],
      ['data', 'issue', 'status'],
      ['data', 'issue', 'workflowState'],
      ['issue', 'state'],
      ['issue', 'status'],
      ['issue', 'workflowState'],
    ])
  );

  if (changedTo !== TARGET_STATUS) {
    return false;
  }

  const changedFrom = normalizeStatusName(
    firstStatus(payload, [
      ['triggerContext', 'previousStatus'],
      ['triggerContext', 'oldStatus'],
      ['previousStatus'],
      ['oldStatus'],
      ['fromStatus'],
      ['previous', 'status'],
      ['previous', 'state'],
      ['data', 'previous', 'status'],
      ['data', 'previous', 'state'],
      ['data', 'previous', 'workflowState'],
      ['data', 'issue', 'previous', 'status'],
      ['data', 'issue', 'previous', 'state'],
    ])
  );

  return changedFrom !== TARGET_STATUS;
}

function shouldMarkResearch(payload) {
  return Boolean(payload && hasStatusChangeMarker(payload) && changedToResearch(payload));
}

function withResearchPrefix(title) {
  const safeTitle = (title || '').trim();
  if (!safeTitle) {
    return RESEARCH_PREFIX;
  }

  if (normalizeText(safeTitle).startsWith(normalizeText(RESEARCH_PREFIX))) {
    return safeTitle;
  }

  return `${RESEARCH_PREFIX}: ${safeTitle}`;
}

function issueIdFrom(payload) {
  return firstString(payload, [
    ['triggerContext', 'id'],
    ['triggerContext', 'issueId'],
    ['triggerContext', 'issue_id'],
    ['triggerContext', 'identifier'],
    ['triggerContext', 'key'],
    ['data', 'id'],
    ['data', 'issueId'],
    ['data', 'issue_id'],
    ['data', 'identifier'],
    ['data', 'key'],
    ['data', 'issue', 'id'],
    ['data', 'issue', 'issueId'],
    ['data', 'issue', 'identifier'],
    ['issue', 'id'],
    ['issue', 'issueId'],
    ['issue', 'identifier'],
    ['id'],
    ['issueId'],
    ['issue_id'],
    ['identifier'],
    ['key'],
  ]);
}

function titleFrom(payload) {
  return firstString(payload, [
    ['triggerContext', 'title'],
    ['data', 'title'],
    ['data', 'issue', 'title'],
    ['issue', 'title'],
    ['title'],
  ]);
}

function buildIssueTitleUpdate(payload) {
  if (!shouldMarkResearch(payload)) {
    return null;
  }

  const issueId = issueIdFrom(payload);
  const title = titleFrom(payload);
  if (!issueId) {
    return null;
  }

  const nextTitle = withResearchPrefix(title);
  if (title && nextTitle === title.trim()) {
    return null;
  }

  return {
    action: 'update_issue_title',
    issueId,
    title: nextTitle,
  };
}

module.exports = {
  RESEARCH_PREFIX,
  TARGET_STATUS,
  buildIssueTitleUpdate,
  normalizeStatusName,
  shouldMarkResearch,
  withResearchPrefix,
};
