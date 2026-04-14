const { handleLinearWebhook } = require('../src/handler');

describe('handleLinearWebhook', () => {
  test('skips non-matching events', async () => {
    const payload = { type: 'Issue', action: 'create', data: {} };
    const result = await handleLinearWebhook(payload, { apiKey: 'test' });
    expect(result).toEqual({ changed: false, reason: 'not_research_status_change' });
  });

  test('updates title when issue enters to research', async () => {
    const fetchImpl = jest.fn().mockResolvedValue({
      ok: true,
      json: async () => ({ data: { issueUpdate: { success: true } } }),
    });

    const payload = {
      type: 'Issue',
      action: 'update',
      data: {
        id: 'POI-4447',
        title: 'Basic outlier flagging on meter readings',
        previous: { state: { name: 'Todo' } },
        state: { name: 'To Research' },
      },
    };

    const result = await handleLinearWebhook(payload, { apiKey: 'linear_test', fetchImpl });

    expect(result.changed).toBe(true);
    expect(result.reason).toBe('updated');
    expect(result.title).toBe('Cursor researching: Basic outlier flagging on meter readings');

    const call = fetchImpl.mock.calls[0];
    const requestBody = JSON.parse(call[1].body);
    expect(requestBody.variables.id).toBe('POI-4447');
    expect(requestBody.variables.input.title).toBe(result.title);
  });

  test('does not call API when title already prefixed', async () => {
    const fetchImpl = jest.fn();

    const payload = {
      type: 'Issue',
      action: 'update',
      data: {
        id: 'POI-4447',
        title: 'Cursor researching: Already set',
        previous: { state: { name: 'Todo' } },
        state: { name: 'To Research' },
      },
    };

    const result = await handleLinearWebhook(payload, { apiKey: 'linear_test', fetchImpl });

    expect(result).toEqual({ changed: false, reason: 'title_already_prefixed' });
    expect(fetchImpl).not.toHaveBeenCalled();
  });
});
