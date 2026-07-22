import { useQuery } from '@tanstack/react-query';

import { apiClient } from './client';

export interface MemberAttendanceRow {
  userId: string;
  fullName: string;
  phoneNumber: string;
  isPaused: boolean;
  lastQualifyingAt: Date | null;
  qualifyingCount12mo: number;
  compliant: boolean;
  communityCount: number;
  noShowCount: number;
  cancelCount: number;
  monthsSinceLastQualifying: number | null;
  isPauseCandidate: boolean;
}

interface WireRow {
  user_id: string;
  full_name: string;
  phone_number: string;
  is_paused: boolean;
  last_qualifying_at: string | null;
  qualifying_count_12mo: number;
  compliant: boolean;
  community_count: number;
  no_show_count: number;
  cancel_count: number;
  months_since_last_qualifying: number | null;
  is_pause_candidate: boolean;
}

interface WireResponse {
  members: WireRow[];
}

function mapRow(w: WireRow): MemberAttendanceRow {
  return {
    userId: w.user_id,
    fullName: w.full_name,
    phoneNumber: w.phone_number,
    isPaused: w.is_paused,
    lastQualifyingAt: w.last_qualifying_at ? new Date(w.last_qualifying_at) : null,
    qualifyingCount12mo: w.qualifying_count_12mo,
    compliant: w.compliant,
    communityCount: w.community_count,
    noShowCount: w.no_show_count,
    cancelCount: w.cancel_count,
    monthsSinceLastQualifying: w.months_since_last_qualifying,
    isPauseCandidate: w.is_pause_candidate,
  };
}

export const memberAttendanceAnalyticsKey = ['member-attendance-analytics'] as const;

export function useMemberAttendanceAnalytics() {
  return useQuery({
    queryKey: memberAttendanceAnalyticsKey,
    queryFn: async () => {
      const { data } = await apiClient.get<WireResponse>(
        '/api/community/events/attendance-analytics/members/',
      );
      return data.members.map(mapRow);
    },
  });
}
