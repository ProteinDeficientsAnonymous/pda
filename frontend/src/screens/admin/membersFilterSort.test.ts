import { describe, expect, it } from 'vitest';

import { makeMember } from '@/test/fixtures';

import { filterAndSort, type StatusFilter } from './membersFilterSort';

const attendedAndInWhatsapp = makeMember({
  id: 'm1',
  fullName: 'Ada',
  lastAttendedAt: new Date('2026-01-05T00:00:00Z'),
  hasJoinedWhatsapp: true,
});
const neverAttended = makeMember({
  id: 'm2',
  fullName: 'Grace',
  lastAttendedAt: null,
  hasJoinedWhatsapp: true,
});
const notInWhatsapp = makeMember({
  id: 'm3',
  fullName: 'Alan',
  lastAttendedAt: new Date('2026-01-05T00:00:00Z'),
  hasJoinedWhatsapp: false,
});
const neitherOne = makeMember({
  id: 'm4',
  fullName: 'Katherine',
  lastAttendedAt: null,
  hasJoinedWhatsapp: false,
});

const all = [attendedAndInWhatsapp, neverAttended, notInWhatsapp, neitherOne];

function ids(statuses: StatusFilter[]): string[] {
  return filterAndSort(all, '', 'name', new Set(), new Set(statuses)).map((m) => m.id);
}

describe('status filters', () => {
  it('returns everyone when nothing is selected', () => {
    expect(ids([]).sort()).toEqual(['m1', 'm2', 'm3', 'm4']);
  });

  it('keeps only members who never attended an event', () => {
    expect(ids(['neverAttended']).sort()).toEqual(['m2', 'm4']);
  });

  it('keeps only members not in whatsapp', () => {
    expect(ids(['notInWhatsapp']).sort()).toEqual(['m3', 'm4']);
  });

  it('requires both when both are selected', () => {
    expect(ids(['neverAttended', 'notInWhatsapp'])).toEqual(['m4']);
  });

  it('combines with search and role filters', () => {
    const result = filterAndSort(all, 'kath', 'name', new Set(), new Set(['neverAttended']));
    expect(result.map((m) => m.id)).toEqual(['m4']);
  });
});
