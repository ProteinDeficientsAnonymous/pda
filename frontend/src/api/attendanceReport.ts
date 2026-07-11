import { useQuery } from '@tanstack/react-query';

import { apiClient } from './client';

export interface EventAttendanceRow {
  eventId: string;
  title: string;
  startDatetime: Date | null;
  attendedCount: number;
  noShowCount: number;
  goingCount: number;
}

interface WireRow {
  event_id: string;
  title: string;
  start_datetime: string | null;
  attended_count: number;
  no_show_count: number;
  going_count: number;
}

interface WireReport {
  events: WireRow[];
}

function mapRow(w: WireRow): EventAttendanceRow {
  return {
    eventId: w.event_id,
    title: w.title,
    startDatetime: w.start_datetime ? new Date(w.start_datetime) : null,
    attendedCount: w.attended_count,
    noShowCount: w.no_show_count,
    goingCount: w.going_count,
  };
}

export function useAttendanceReport() {
  return useQuery({
    queryKey: ['attendance-report'] as const,
    queryFn: async () => {
      const { data } = await apiClient.get<WireReport>('/api/community/events/attendance-report/');
      return data.events.map(mapRow);
    },
  });
}
