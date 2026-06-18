'use strict';

const assert = require('node:assert/strict');
const test = require('node:test');

const { createLinearClient } = require('../src');

test('sends an issue title update mutation to Linear', async () => {
  const requests = [];
  const client = createLinearClient({
    apiKey: 'test-api-key',
    async fetchImpl(url, options) {
      requests.push({ url, options });

      return {
        ok: true,
        status: 200,
        async json() {
          return {
            data: {
              issueUpdate: {
                success: true,
                issue: {
                  id: 'POI-4599',
                  title: 'Cursor researching: Cant close Jan 2025 for Trading Account'
                }
              }
            }
          };
        }
      };
    }
  });

  const issue = await client.updateIssueTitle(
    'POI-4599',
    'Cursor researching: Cant close Jan 2025 for Trading Account'
  );

  assert.deepEqual(issue, {
    id: 'POI-4599',
    title: 'Cursor researching: Cant close Jan 2025 for Trading Account'
  });
  assert.equal(requests.length, 1);
  assert.equal(requests[0].url, 'https://api.linear.app/graphql');
  assert.equal(requests[0].options.method, 'POST');
  assert.equal(requests[0].options.headers.Authorization, 'test-api-key');
  assert.deepEqual(JSON.parse(requests[0].options.body).variables, {
    id: 'POI-4599',
    input: {
      title: 'Cursor researching: Cant close Jan 2025 for Trading Account'
    }
  });
});

test('requires a Linear API key', () => {
  assert.throws(() => createLinearClient(), /LINEAR_API_KEY/);
});
