import type { Member } from '@/api/users';

export function isAttendancePaused(member: Pick<Member, 'attendancePausedAt'>): boolean {
  return member.attendancePausedAt !== null;
}

// Attendance pause clears is_member, but admins still manage them as members.
export function isManagedMember(member: Pick<Member, 'isMember' | 'attendancePausedAt'>): boolean {
  return member.isMember || isAttendancePaused(member);
}
