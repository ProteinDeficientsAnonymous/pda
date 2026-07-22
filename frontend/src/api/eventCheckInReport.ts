import { useQuery } from '@tanstack/react-query';

import { apiClient } from './client';

export interface CheckInReportPerson {
  userId: string;
  name: string;
  phone: string | null;
  isMember: boolean;
}

export interface AttendedPerson extends CheckInReportPerson {
  checkedInAt: Date | null;
}

export interface CanceledPerson extends CheckInReportPerson {
  cancelledAt: Date;
}

export interface CheckInReport {
  attendedCount: number;
  noShowCount: number;
  canceledCount: number;
  unmarkedCount: number;
  attended: AttendedPerson[];
  noShows: CheckInReportPerson[];
  canceled: CanceledPerson[];
  unmarked: CheckInReportPerson[];
}

interface WirePerson {
  user_id: string;
  name: string;
  phone: string | null;
  is_member: boolean;
}

interface WireAttendedPerson extends WirePerson {
  checked_in_at: string | null;
}

interface WireCanceledPerson extends WirePerson {
  cancelled_at: string;
}

interface WireReport {
  attended_count: number;
  no_show_count: number;
  canceled_count: number;
  unmarked_count: number;
  attended: WireAttendedPerson[];
  no_shows: WirePerson[];
  canceled: WireCanceledPerson[];
  unmarked: WirePerson[];
}

function mapReport(w: WireReport): CheckInReport {
  return {
    attendedCount: w.attended_count,
    noShowCount: w.no_show_count,
    canceledCount: w.canceled_count,
    unmarkedCount: w.unmarked_count,
    attended: w.attended.map((p) => ({
      userId: p.user_id,
      name: p.name,
      phone: p.phone,
      isMember: p.is_member,
      checkedInAt: p.checked_in_at ? new Date(p.checked_in_at) : null,
    })),
    noShows: w.no_shows.map((p) => ({
      userId: p.user_id,
      name: p.name,
      phone: p.phone,
      isMember: p.is_member,
    })),
    canceled: w.canceled.map((p) => ({
      userId: p.user_id,
      name: p.name,
      phone: p.phone,
      isMember: p.is_member,
      cancelledAt: new Date(p.cancelled_at),
    })),
    unmarked: w.unmarked.map((p) => ({
      userId: p.user_id,
      name: p.name,
      phone: p.phone,
      isMember: p.is_member,
    })),
  };
}

export const CSV_COLUMNS = [
  { key: 'name', label: 'name' },
  { key: 'phone', label: 'phone' },
  { key: 'rsvp_status', label: 'rsvp status' },
  { key: 'attendance', label: 'attendance' },
  { key: 'checked_in_at', label: 'checked-in time' },
  { key: 'cancelled_at', label: 'canceled time' },
  { key: 'plus_one', label: 'plus-one' },
] as const;

export const checkInReportKeys = {
  detail: (eventId: string) => ['event-check-in-report', eventId] as const,
};

export function useCheckInReport(eventId: string | undefined) {
  const id = eventId ?? '';
  return useQuery({
    queryKey: checkInReportKeys.detail(id),
    queryFn: async () => {
      const { data } = await apiClient.get<WireReport>(
        `/api/community/events/${id}/report/`,
      );
      return mapReport(data);
    },
    enabled: Boolean(eventId),
  });
}

export async function downloadCheckInReportCsv(eventId: string, columns: string[]): Promise<void> {
  const { data } = await apiClient.get<Blob>(`/api/community/events/${eventId}/report.csv`, {
    params: { columns: columns.join(',') },
    responseType: 'blob',
  });
  const url = URL.createObjectURL(data);
  const link = document.createElement('a');
  link.href = url;
  link.download = `check-in-report-${eventId}.csv`;
  document.body.appendChild(link);
  link.click();
  link.remove();
  URL.revokeObjectURL(url);
}
