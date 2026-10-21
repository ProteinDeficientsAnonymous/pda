import { useMutation, useQueryClient } from '@tanstack/react-query';

import { extractApiErrorOr } from './apiErrors';
import { attendanceReportKey } from './attendanceReport';
import { apiClient } from './client';
import { eventKeys } from './events';
import { memberAttendanceAnalyticsKey } from './memberAttendanceAnalytics';
import { USERS_KEY } from './users';

export function reportMarkAttendanceError(err: unknown): string {
  return extractApiErrorOr(err, "couldn't mark attendance — try again");
}

export interface MarkAttendanceInput {
  eventId?: string;
  eventTitle?: string;
  eventDate?: string;
  eventType?: string;
  userIds: string[];
}

interface WireMarkOut {
  event_id: string;
  event_title: string;
  created_count: number;
  updated_count: number;
  skipped_count: number;
}

export function useMarkAttendance() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: async (input: MarkAttendanceInput) => {
      const { data } = await apiClient.post<WireMarkOut>('/api/community/events/attendance-mark/', {
        event_id: input.eventId,
        event_title: input.eventTitle,
        event_date: input.eventDate,
        event_type: input.eventType,
        user_ids: input.userIds,
      });
      return {
        eventId: data.event_id,
        eventTitle: data.event_title,
        createdCount: data.created_count,
        updatedCount: data.updated_count,
        skippedCount: data.skipped_count,
      };
    },
    onSuccess: () => {
      void qc.invalidateQueries({ queryKey: attendanceReportKey });
      void qc.invalidateQueries({ queryKey: memberAttendanceAnalyticsKey });
      void qc.invalidateQueries({ queryKey: USERS_KEY });
      void qc.invalidateQueries({ queryKey: eventKeys.all });
    },
  });
}
