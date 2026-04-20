import { describe, it, expect } from 'vitest';
import { sortOptionsChrono, pickFinalizeDefault, sortOptionsByVotes } from './pollHelpers';
import type { EventPollOption } from '@/models/eventPoll';

function opt(overrides: Partial<EventPollOption> = {}): EventPollOption {
  return {
    id: 'x',
    datetime: new Date('2026-05-01T18:00:00Z'),
    displayOrder: 0,
    yesCount: 0,
    maybeCount: 0,
    noCount: 0,
    yesVoters: [],
    maybeVoters: [],
    noVoters: [],
    ...overrides,
  };
}

describe('sortOptionsChrono', () => {
  it('sorts earliest datetime first', () => {
    const a = opt({ id: 'a', datetime: new Date('2026-05-02T18:00:00Z') });
    const b = opt({ id: 'b', datetime: new Date('2026-05-01T18:00:00Z') });
    const c = opt({ id: 'c', datetime: new Date('2026-05-03T18:00:00Z') });
    const sorted = sortOptionsChrono([a, b, c]);
    expect(sorted.map((o) => o.id)).toEqual(['b', 'a', 'c']);
  });

  it('falls back to displayOrder when datetimes match', () => {
    const dt = new Date('2026-05-01T18:00:00Z');
    const a = opt({ id: 'a', datetime: dt, displayOrder: 2 });
    const b = opt({ id: 'b', datetime: dt, displayOrder: 0 });
    const sorted = sortOptionsChrono([a, b]);
    expect(sorted.map((o) => o.id)).toEqual(['b', 'a']);
  });

  it('does not mutate the input', () => {
    const input = [
      opt({ id: 'a', datetime: new Date('2026-05-02T18:00:00Z') }),
      opt({ id: 'b', datetime: new Date('2026-05-01T18:00:00Z') }),
    ];
    sortOptionsChrono(input);
    expect(input.map((o) => o.id)).toEqual(['a', 'b']);
  });
});

describe('pickFinalizeDefault', () => {
  it('returns null for an empty list', () => {
    expect(pickFinalizeDefault([])).toBeNull();
  });

  it('picks the highest yes_count', () => {
    const a = opt({ id: 'a', yesCount: 1 });
    const b = opt({ id: 'b', yesCount: 3 });
    const c = opt({ id: 'c', yesCount: 2 });
    expect(pickFinalizeDefault([a, b, c])?.id).toBe('b');
  });

  it('breaks ties by earliest datetime', () => {
    const a = opt({ id: 'a', yesCount: 3, datetime: new Date('2026-05-02T18:00:00Z') });
    const b = opt({ id: 'b', yesCount: 3, datetime: new Date('2026-05-01T18:00:00Z') });
    expect(pickFinalizeDefault([a, b])?.id).toBe('b');
  });
});

describe('sortOptionsByVotes', () => {
  it('sorts by descending yesCount first', () => {
    const a = opt({ id: 'a', yesCount: 1 });
    const b = opt({ id: 'b', yesCount: 3 });
    const c = opt({ id: 'c', yesCount: 2 });
    const sorted = sortOptionsByVotes([a, b, c]);
    expect(sorted.map((o) => o.id)).toEqual(['b', 'c', 'a']);
  });

  it('breaks yes ties by descending maybeCount', () => {
    const a = opt({ id: 'a', yesCount: 2, maybeCount: 1 });
    const b = opt({ id: 'b', yesCount: 2, maybeCount: 3 });
    const c = opt({ id: 'c', yesCount: 2, maybeCount: 2 });
    const sorted = sortOptionsByVotes([a, b, c]);
    expect(sorted.map((o) => o.id)).toEqual(['b', 'c', 'a']);
  });

  it('falls back to earliest datetime when yes and maybe counts tie', () => {
    const a = opt({
      id: 'a',
      yesCount: 2,
      maybeCount: 1,
      datetime: new Date('2026-05-03T18:00:00Z'),
    });
    const b = opt({
      id: 'b',
      yesCount: 2,
      maybeCount: 1,
      datetime: new Date('2026-05-01T18:00:00Z'),
    });
    const c = opt({
      id: 'c',
      yesCount: 2,
      maybeCount: 1,
      datetime: new Date('2026-05-02T18:00:00Z'),
    });
    const sorted = sortOptionsByVotes([a, b, c]);
    expect(sorted.map((o) => o.id)).toEqual(['b', 'c', 'a']);
  });

  it('does not mutate the input', () => {
    const input = [
      opt({ id: 'a', yesCount: 1 }),
      opt({ id: 'b', yesCount: 3 }),
      opt({ id: 'c', yesCount: 2 }),
    ];
    sortOptionsByVotes(input);
    expect(input.map((o) => o.id)).toEqual(['a', 'b', 'c']);
  });
});
