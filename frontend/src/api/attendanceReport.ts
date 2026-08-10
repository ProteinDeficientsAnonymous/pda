import { useQuery } from '@tanstack/react-query';

import { apiClient } from './client';

export interface EventAttendanceRow {
  eventId: string;
  title: string;
  eventType: string;
  startDatetime: Date | null;
  attendedCount: number;
  noShowCount: number;
  goingCount: number;
}

export interface AttendanceReportData {
  events: EventAttendanceRow[];
  officialNoShowCount: number;
  clubNoShowCount: number;
}

interface WireRow {
  event_id: string;
  title: string;
  event_type: string;
  start_datetime: string | null;
  attended_count: number;
  no_show_count: number;
  going_count: number;
}

interface WireReport {
  events: WireRow[];
  official_no_show_count: number;
  club_no_show_count: number;
}

function mapRow(w: WireRow): EventAttendanceRow {
  return {
    eventId: w.event_id,
    title: w.title,
    eventType: w.event_type,
    startDatetime: w.start_datetime ? new Date(w.start_datetime) : null,
    attendedCount: w.attended_count,
    noShowCount: w.no_show_count,
    goingCount: w.going_count,
  };
}

export const attendanceReportKey = ['attendance-report'] as const;

export function useAttendanceReport() {
  return useQuery({
    queryKey: attendanceReportKey,
    queryFn: async () => {
      const { data } = await apiClient.get<WireReport>('/api/community/events/attendance-report/');
      return {
        events: data.events.map(mapRow),
        officialNoShowCount: data.official_no_show_count,
        clubNoShowCount: data.club_no_show_count,
      };
    },
  });
}
