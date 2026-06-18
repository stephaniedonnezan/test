'use strict';

const assert = require('node:assert/strict');
const test = require('node:test');

const {
  addCursorResearchingToTitle,
  handleIssueStatusChangedToResearch,
  isToResearchStatus
} = require('../src/linearResearchTitle');

test('recognizes to research status regardless of case and extra spaces', () => {
  assert.equal(isToResearchStatus('to research'), true);
  assert.equal(isToResearchStatus(' To   Research '), true);
  assert.equal(isToResearchStatus('researching'), false);
});

test('adds the cursor researching marker to an unmarked title', () => {
  assert.equal(
    addCursorResearchingToTitle('Cant close Jan 2025 for Trading Account'),
    'Cursor researching: Cant close Jan 2025 for Trading Account'
  );
});

test('does not duplicate the cursor researching marker', () => {
  assert.equal(
    addCursorResearchingToTitle('Cursor researching: Cant close Jan 2025 for Trading Account'),
    'Cursor researching: Cant close Jan 2025 for Trading Account'
  );
});

test('updates Linear issue title when an issue status changes to to research', async () => {
  const calls = [];
  const result = await handleIssueStatusChangedToResearch(
    {
      triggerType: 'linear',
      webhookType: 'issue',
      trigger: 'status_changed',
      newStatus: 'To Research',
      id: 'POI-4599',
      title: 'Cant close Jan 2025 for Trading Account'
    },
    {
      async updateIssueTitle(issueId, title) {
        calls.push({ issueId, title });
      }
    }
  );

  assert.deepEqual(calls, [
    {
      issueId: 'POI-4599',
      title: 'Cursor researching: Cant close Jan 2025 for Trading Account'
    }
  ]);
  assert.deepEqual(result, {
    updated: true,
    issueId: 'POI-4599',
    title: 'Cursor researching: Cant close Jan 2025 for Trading Account'
  });
});

test('ignores issue status changes to other statuses', async () => {
  const calls = [];
  const result = await handleIssueStatusChangedToResearch(
    {
      triggerType: 'linear',
      webhookType: 'issue',
      trigger: 'status_changed',
      newStatus: 'Canceled',
      id: 'POI-4599',
      title: 'Cant close Jan 2025 for Trading Account'
    },
    {
      async updateIssueTitle(issueId, title) {
        calls.push({ issueId, title });
      }
    }
  );

  assert.deepEqual(calls, []);
  assert.deepEqual(result, { updated: false, reason: 'ignored_status' });
});

test('ignores non-status-change events', async () => {
  const calls = [];
  const result = await handleIssueStatusChangedToResearch(
    {
      triggerType: 'linear',
      webhookType: 'issue',
      trigger: 'comment_created',
      newStatus: 'To Research',
      id: 'POI-4599',
      title: 'Cant close Jan 2025 for Trading Account'
    },
    {
      async updateIssueTitle(issueId, title) {
        calls.push({ issueId, title });
      }
    }
  );

  assert.deepEqual(calls, []);
  assert.deepEqual(result, { updated: false, reason: 'ignored_event' });
});

test('does not update an issue title that is already marked', async () => {
  const calls = [];
  const result = await handleIssueStatusChangedToResearch(
    {
      triggerType: 'linear',
      webhookType: 'issue',
      trigger: 'status_changed',
      newStatus: 'To Research',
      id: 'POI-4599',
      title: 'Cursor researching: Cant close Jan 2025 for Trading Account'
    },
    {
      async updateIssueTitle(issueId, title) {
        calls.push({ issueId, title });
      }
    }
  );

  assert.deepEqual(calls, []);
  assert.deepEqual(result, {
    updated: false,
    reason: 'already_marked',
    title: 'Cursor researching: Cant close Jan 2025 for Trading Account'
  });
});
