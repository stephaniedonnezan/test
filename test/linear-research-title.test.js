import assert from 'node:assert/strict';
import { describe, it } from 'node:test';

import {
  buildResearchingTitle,
  markResearchingTitleForPayload,
  shouldMarkIssueAsResearching,
} from '../src/linear-research-title.js';

describe('buildResearchingTitle', () => {
  it('prefixes issue titles with the Cursor researching marker', () => {
    assert.equal(
      buildResearchingTitle('Remove Subscribe button on invite'),
      'Cursor researching: Remove Subscribe button on invite'
    );
  });

  it('does not duplicate an existing Cursor researching prefix', () => {
    assert.equal(
      buildResearchingTitle('Cursor researching: Remove Subscribe button on invite'),
      'Cursor researching: Remove Subscribe button on invite'
    );
    assert.equal(
      buildResearchingTitle('[Cursor researching] Remove Subscribe button on invite'),
      '[Cursor researching] Remove Subscribe button on invite'
    );
  });
});

describe('shouldMarkIssueAsResearching', () => {
  it('matches Cursor automation payloads for issue status changes to to research', () => {
    assert.equal(
      shouldMarkIssueAsResearching({
        triggerContext: {
          triggerType: 'linear',
          webhookType: 'issue',
          trigger: 'status_changed',
          newStatus: 'To Research',
        },
      }),
      true
    );
  });

  it('matches Linear issue webhooks when the state changes to to research', () => {
    assert.equal(
      shouldMarkIssueAsResearching({
        action: 'update',
        type: 'Issue',
        updatedFrom: { stateId: 'previous-state-id' },
        data: {
          state: { name: 'to-research' },
        },
      }),
      true
    );
  });

  it('ignores non-target statuses', () => {
    assert.equal(
      shouldMarkIssueAsResearching({
        triggerContext: {
          triggerType: 'linear',
          webhookType: 'issue',
          trigger: 'status_changed',
          newStatus: 'Done',
        },
      }),
      false
    );
  });
});

describe('markResearchingTitleForPayload', () => {
  it('returns a dry-run result without calling Linear', async () => {
    const result = await markResearchingTitleForPayload(
      {
        triggerContext: {
          triggerType: 'linear',
          webhookType: 'issue',
          trigger: 'status_changed',
          newStatus: 'to research',
          id: 'POI-4961',
          title: 'Remove Subscribe button on invite',
        },
      },
      { dryRun: true }
    );

    assert.deepEqual(result, {
      updated: false,
      reason: 'dry-run',
      title: 'Cursor researching: Remove Subscribe button on invite',
      issue: {
        id: 'POI-4961',
        title: 'Remove Subscribe button on invite',
        url: null,
      },
    });
  });

  it('fetches the current Linear issue and updates its title', async () => {
    const calls = [];
    const fetchImpl = async (_url, request) => {
      const body = JSON.parse(request.body);
      calls.push({ request, body });

      if (body.query.includes('query IssueForResearchTitle')) {
        return Response.json({
          data: {
            issue: {
              id: 'linear-uuid',
              identifier: 'POI-4961',
              title: 'Remove Subscribe button on invite',
            },
          },
        });
      }

      assert.equal(body.variables.id, 'linear-uuid');
      assert.equal(body.variables.title, 'Cursor researching: Remove Subscribe button on invite');

      return Response.json({
        data: {
          issueUpdate: {
            success: true,
            issue: {
              id: 'linear-uuid',
              identifier: 'POI-4961',
              title: body.variables.title,
            },
          },
        },
      });
    };

    const result = await markResearchingTitleForPayload(
      {
        triggerContext: {
          triggerType: 'linear',
          webhookType: 'issue',
          trigger: 'status_changed',
          newStatus: 'To Research',
          id: 'POI-4961',
        },
      },
      {
        apiKey: 'lin_api_key',
        fetchImpl,
      }
    );

    assert.equal(result.updated, true);
    assert.equal(result.previousTitle, 'Remove Subscribe button on invite');
    assert.equal(result.title, 'Cursor researching: Remove Subscribe button on invite');
    assert.equal(calls.length, 2);
    assert.equal(calls[0].request.headers.Authorization, 'lin_api_key');
  });
});
