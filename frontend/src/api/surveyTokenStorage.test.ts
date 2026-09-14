import { describe, expect, it } from 'vitest';

import { getStoredSurveyToken, setStoredSurveyToken } from './surveyTokenStorage';

describe('surveyTokenStorage', () => {
  it('returns null when nothing is stored for the slug', () => {
    expect(getStoredSurveyToken('nothing-here')).toBeNull();
  });

  it('stores and reads a token per slug', () => {
    setStoredSurveyToken('a', 'tok-a');
    setStoredSurveyToken('b', 'tok-b');
    expect(getStoredSurveyToken('a')).toBe('tok-a');
    expect(getStoredSurveyToken('b')).toBe('tok-b');
  });

  it('overwrites an existing token for the same slug', () => {
    setStoredSurveyToken('a', 'old');
    setStoredSurveyToken('a', 'new');
    expect(getStoredSurveyToken('a')).toBe('new');
  });
});
