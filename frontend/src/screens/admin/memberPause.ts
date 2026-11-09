import type { Member } from '@/api/users';
import { MembershipStatus, type MembershipStatusValue } from '@/models/user';

const MANAGED_STATUSES: readonly MembershipStatusValue[] = [
  MembershipStatus.Member,
  MembershipStatus.AttendancePaused,
  MembershipStatus.Archived,
];

export function isAttendancePaused(member: Pick<Member, 'attendancePausedAt'>): boolean {
  return member.attendancePausedAt !== null;
}

export function isManagedMember(member: Pick<Member, 'membershipStatus'>): boolean {
  return MANAGED_STATUSES.includes(member.membershipStatus);
}
