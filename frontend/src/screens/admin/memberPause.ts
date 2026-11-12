import type { Member } from '@/api/users';
import { MEMBER_STATUSES, MembershipStatus, type MembershipStatusValue } from '@/models/user';

const MANAGED_STATUSES: readonly MembershipStatusValue[] = [
  ...MEMBER_STATUSES,
  MembershipStatus.Tentative,
];

export function isAttendancePaused(member: Pick<Member, 'attendancePausedAt'>): boolean {
  return member.attendancePausedAt !== null;
}

export function isTentative(member: Pick<Member, 'membershipStatus'>): boolean {
  return member.membershipStatus === MembershipStatus.Tentative;
}

export function isManagedMember(member: Pick<Member, 'membershipStatus'>): boolean {
  return MANAGED_STATUSES.includes(member.membershipStatus);
}
