import assert from 'node:assert/strict';
import test from 'node:test';

import {
  handleLinearStatusChanged,
  isStatusChangedToResearch,
  titleWithCursorResearching
} from './linear-title-researching.mjs';

const automationPayload = {
  triggerContext: {
    webhookType: 'issue',
    trigger: 'status_changed',
    newStatus: 'To Research',
    id: 'POI-4838',
    title: 'Redesign of "Add Input"'
  }
};

test('detects Linear issue status changes to to research', () => {
  assert.equal(isStatusChangedToResearch(automationPayload), true);
});

test('ignores non-research statuses', () => {
  assert.equal(
    isStatusChangedToResearch({
      triggerContext: {
        webhookType: 'issue',
        trigger: 'status_changed',
        newStatus: 'In Review',
        id: 'POI-4838',
        title: 'Redesign of "Add Input"'
      }
    }),
    false
  );
});

test('adds the Cursor researching prefix once', () => {
  assert.equal(titleWithCursorResearching('Redesign of "Add Input"'), 'Cursor researching: Redesign of "Add Input"');
  assert.equal(
    titleWithCursorResearching('Cursor researching: Redesign of "Add Input"'),
    'Cursor researching: Redesign of "Add Input"'
  );
});

test('updates the Linear issue title for a qualifying payload', async () => {
  const requests = [];
  const fetchImpl = async (url, options) => {
    requests.push({ url, options });
    return {
      ok: true,
      async json() {
        return {
          data: {
            issueUpdate: {
              success: true,
              issue: {
                id: 'POI-4838',
                title: 'Cursor researching: Redesign of "Add Input"'
              }
            }
          }
        };
      }
    };
  };

  const result = await handleLinearStatusChanged(automationPayload, {
    apiKey: 'linear-api-key',
    fetchImpl
  });

  assert.equal(result.changed, true);
  assert.equal(requests.length, 1);
  assert.equal(requests[0].url, 'https://api.linear.app/graphql');
  assert.equal(requests[0].options.headers.Authorization, 'linear-api-key');
  assert.deepEqual(JSON.parse(requests[0].options.body).variables, {
    id: 'POI-4838',
    title: 'Cursor researching: Redesign of "Add Input"'
  });
});

test('does not call Linear when the title is already marked', async () => {
  let called = false;

  const result = await handleLinearStatusChanged(
    {
      ...automationPayload,
      triggerContext: {
        ...automationPayload.triggerContext,
        title: 'Cursor researching: Redesign of "Add Input"'
      }
    },
    {
      apiKey: 'linear-api-key',
      fetchImpl: async () => {
        called = true;
      }
    }
  );

  assert.equal(result.changed, false);
  assert.equal(result.reason, 'title_already_marked');
  assert.equal(called, false);
});
