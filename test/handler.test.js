const assert = require('node:assert/strict');
const test = require('node:test');

const { handleLinearWebhook } = require('../src/handler');

test('skips payloads that do not need a title update', async () => {
  const result = await handleLinearWebhook({
    triggerContext: {
      trigger: 'status_changed',
      newStatus: 'Done',
      id: 'POI-4178',
      title: 'Preview POS link disappears',
    },
  });

  assert.deepEqual(result, { changed: false, reason: 'no_title_update_needed' });
});

test('updates the Linear issue title when the issue enters to research', async () => {
  const fetchCalls = [];
  const fetchImpl = async (...args) => {
    fetchCalls.push(args);
    return {
      ok: true,
      json: async () => ({ data: { issueUpdate: { success: true } } }),
    };
  };

  const result = await handleLinearWebhook(
    {
      triggerContext: {
        trigger: 'status_changed',
        newStatus: 'To Research',
        id: 'POI-4178',
        title: 'UBA download button disappears',
      },
    },
    { apiKey: 'linear_test', fetchImpl }
  );

  assert.equal(result.changed, true);
  assert.equal(result.reason, 'updated');
  assert.equal(result.action, 'update_issue_title');
  assert.equal(result.issueId, 'POI-4178');
  assert.equal(result.title, 'Cursor researching: UBA download button disappears');

  assert.equal(fetchCalls.length, 1);
  assert.equal(fetchCalls[0][0], 'https://api.linear.app/graphql');
  assert.equal(fetchCalls[0][1].method, 'POST');

  const requestBody = JSON.parse(fetchCalls[0][1].body);
  assert.equal(requestBody.variables.id, 'POI-4178');
  assert.deepEqual(requestBody.variables.input, {
    title: 'Cursor researching: UBA download button disappears',
  });
});

test('does not call Linear when the title is already prefixed', async () => {
  const fetchImpl = async () => {
    throw new Error('fetch should not be called');
  };

  const result = await handleLinearWebhook(
    {
      triggerContext: {
        trigger: 'status_changed',
        newStatus: 'To Research',
        id: 'POI-4178',
        title: 'Cursor researching: Already set',
      },
    },
    { apiKey: 'linear_test', fetchImpl }
  );

  assert.deepEqual(result, { changed: false, reason: 'no_title_update_needed' });
});
