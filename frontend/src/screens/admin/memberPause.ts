import type { Member } from '@/api/users';
import { MembershipStatus } from '@/models/user';

export function isGuidelinesPaused(member: Pick<Member, 'membershipStatus'>): boolean {
  return member.membershipStatus === MembershipStatus.GuidelinesPaused;
}

export function isAttendancePaused(member: Pick<Member, 'membershipStatus'>): boolean {
  return member.membershipStatus === MembershipStatus.AttendancePaused;
}

// Attendance pause clears is_member, but admins still manage them as members.
export function isManagedMember(member: Pick<Member, 'isMember' | 'membershipStatus'>): boolean {
  return member.isMember || isAttendancePaused(member);
}
