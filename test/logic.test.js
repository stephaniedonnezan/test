const assert = require('node:assert/strict');
const test = require('node:test');

const {
  RESEARCH_PREFIX,
  buildIssueTitleUpdate,
  normalizeStatusName,
  shouldMarkResearch,
  withResearchPrefix,
} = require('../src/logic');

test('normalizes status names across separators, case, and camelCase', () => {
  assert.equal(normalizeStatusName('To Research'), 'to research');
  assert.equal(normalizeStatusName('to_research'), 'to research');
  assert.equal(normalizeStatusName('toResearch'), 'to research');
});

test('detects a flat automation status_changed trigger to to research', () => {
  const payload = {
    triggerContext: {
      trigger: 'status_changed',
      newStatus: 'To Research',
      id: 'POI-4178',
      title: 'UBA download button disappears from Closing page after successful closing',
    },
  };

  assert.equal(shouldMarkResearch(payload), true);
  assert.deepEqual(buildIssueTitleUpdate(payload), {
    action: 'update_issue_title',
    issueId: 'POI-4178',
    title: `${RESEARCH_PREFIX}: UBA download button disappears from Closing page after successful closing`,
  });
});

test('detects a nested Linear issue update into to research', () => {
  const payload = {
    type: 'Issue',
    action: 'update',
    data: {
      id: 'POI-4178',
      title: 'Preview POS link disappears',
      previous: { state: { name: 'Todo' } },
      state: { name: 'to_research' },
    },
  };

  assert.equal(shouldMarkResearch(payload), true);
  assert.deepEqual(buildIssueTitleUpdate(payload), {
    action: 'update_issue_title',
    issueId: 'POI-4178',
    title: `${RESEARCH_PREFIX}: Preview POS link disappears`,
  });
});

test('does not match status changes to other statuses', () => {
  const payload = {
    triggerContext: {
      trigger: 'status_changed',
      newStatus: 'Done',
      id: 'POI-4178',
      title: 'Preview POS link disappears',
    },
  };

  assert.equal(shouldMarkResearch(payload), false);
  assert.equal(buildIssueTitleUpdate(payload), null);
});

test('does not match non-status update payloads', () => {
  const payload = {
    type: 'Issue',
    action: 'update',
    data: {
      id: 'POI-4178',
      title: 'Preview POS link disappears',
    },
  };

  assert.equal(shouldMarkResearch(payload), false);
  assert.equal(buildIssueTitleUpdate(payload), null);
});

test('does not duplicate the research prefix', () => {
  assert.equal(
    withResearchPrefix('cursor researching: Existing title'),
    'cursor researching: Existing title'
  );

  assert.equal(
    buildIssueTitleUpdate({
      triggerContext: {
        trigger: 'status_changed',
        newStatus: 'To Research',
        id: 'POI-4178',
        title: 'Cursor researching: Existing title',
      },
    }),
    null
  );
});

test('adds the research prefix to normal titles', () => {
  assert.equal(
    withResearchPrefix('UBA download button disappears'),
    `${RESEARCH_PREFIX}: UBA download button disappears`
  );
});
