const { shouldMarkResearch, withResearchPrefix, RESEARCH_PREFIX } = require('../src/logic');

describe('shouldMarkResearch', () => {
  test('returns true on Issue update to "to research"', () => {
    const event = {
      type: 'Issue',
      action: 'update',
      data: {
        previous: { state: { name: 'Todo' } },
        state: { name: 'To Research' },
      },
    };

    expect(shouldMarkResearch(event)).toBe(true);
  });

  test('returns false when status did not change', () => {
    const event = {
      type: 'Issue',
      action: 'update',
      data: {
        previous: { state: { name: 'To Research' } },
        state: { name: 'To Research' },
      },
    };

    expect(shouldMarkResearch(event)).toBe(false);
  });

  test('returns false for non-Issue events', () => {
    expect(shouldMarkResearch({ type: 'Comment', action: 'update', data: {} })).toBe(false);
  });
});

describe('withResearchPrefix', () => {
  test('adds prefix to normal titles', () => {
    expect(withResearchPrefix('Basic outlier flagging on meter readings')).toBe(
      `${RESEARCH_PREFIX}: Basic outlier flagging on meter readings`
    );
  });

  test('keeps title if already prefixed (case-insensitive)', () => {
    expect(withResearchPrefix('cursor researching: Existing title')).toBe(
      'cursor researching: Existing title'
    );
  });
});
