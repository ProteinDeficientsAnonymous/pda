import type { Member } from '@/api/users';
import { MEMBER_STATUSES, MembershipStatus, type MembershipStatusValue } from '@/models/user';

const MANAGED_STATUSES: readonly MembershipStatusValue[] = [
  ...MEMBER_STATUSES,
  MembershipStatus.Tentative,
];

export function isGuidelinesPaused(member: Pick<Member, 'membershipStatus'>): boolean {
  return member.membershipStatus === MembershipStatus.GuidelinesPaused;
}

export function isAttendancePaused(member: Pick<Member, 'membershipStatus'>): boolean {
  return member.membershipStatus === MembershipStatus.AttendancePaused;
}

export function isTentative(member: Pick<Member, 'membershipStatus'>): boolean {
  return member.membershipStatus === MembershipStatus.Tentative;
}

export function isManagedMember(member: Pick<Member, 'membershipStatus'>): boolean {
  return MANAGED_STATUSES.includes(member.membershipStatus);
}
