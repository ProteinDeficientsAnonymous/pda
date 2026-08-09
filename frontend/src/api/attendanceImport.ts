import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query';

import { extractApiErrorOr } from './apiErrors';
import { attendanceReportKey } from './attendanceReport';
import { apiClient } from './client';

export function reportAttendanceImportError(err: unknown): string {
  return extractApiErrorOr(err, "couldn't process that — try again");
}

export interface ImportCandidate {
  userId: string;
  fullName: string;
  phoneNumber: string;
}

export interface ImportRow {
  rowIndex: number;
  rawName: string;
  partifulStatus: string;
  checkedIn: boolean;
  matchedUserId: string | null;
  matchedFullName: string | null;
  candidates: ImportCandidate[];
  hasExistingRsvp: boolean;
}

export interface AttendanceImportPreview {
  matched: ImportRow[];
  needsReview: ImportRow[];
}

export interface EventOption {
  id: string;
  title: string;
  startDatetime: Date | null;
}

interface WireCandidate {
  user_id: string;
  full_name: string;
  phone_number: string;
}

interface WireRow {
  row_index: number;
  raw_name: string;
  partiful_status: string;
  checked_in: boolean;
  matched_user_id: string | null;
  matched_full_name: string | null;
  candidates: WireCandidate[];
  has_existing_rsvp: boolean;
}

interface WirePreview {
  matched: WireRow[];
  needs_review: WireRow[];
}

interface WireEventOption {
  id: string;
  title: string;
  start_datetime: string | null;
}

function mapRow(w: WireRow): ImportRow {
  return {
    rowIndex: w.row_index,
    rawName: w.raw_name,
    partifulStatus: w.partiful_status,
    checkedIn: w.checked_in,
    matchedUserId: w.matched_user_id,
    matchedFullName: w.matched_full_name,
    candidates: w.candidates.map((c) => ({
      userId: c.user_id,
      fullName: c.full_name,
      phoneNumber: c.phone_number,
    })),
    hasExistingRsvp: w.has_existing_rsvp,
  };
}

export function useAttendanceImportEventOptions(query: string) {
  return useQuery({
    queryKey: ['attendance-import-events', query],
    queryFn: async () => {
      const { data } = await apiClient.get<WireEventOption[]>(
        '/api/community/events/attendance-import/events/',
        { params: { q: query } },
      );
      return data.map<EventOption>((e) => ({
        id: e.id,
        title: e.title,
        startDatetime: e.start_datetime ? new Date(e.start_datetime) : null,
      }));
    },
    staleTime: 30_000,
  });
}

export function usePreviewAttendanceImport() {
  return useMutation({
    mutationFn: async ({ file, eventId }: { file: File; eventId?: string | undefined }) => {
      const formData = new FormData();
      formData.append('csv_file', file);
      const { data } = await apiClient.post<WirePreview>(
        '/api/community/events/attendance-import/preview/',
        formData,
        {
          headers: { 'Content-Type': 'multipart/form-data' },
          params: eventId ? { event_id: eventId } : undefined,
        },
      );
      return {
        matched: data.matched.map(mapRow),
        needsReview: data.needs_review.map(mapRow),
      } satisfies AttendanceImportPreview;
    },
  });
}

export interface RowResolution {
  rowIndex: number;
  rawName: string;
  partifulStatus: string;
  checkedIn: boolean;
  userId: string | null;
  skip: boolean;
}

export interface CommitAttendanceImportInput {
  eventId?: string;
  eventTitle?: string;
  eventDate?: string;
  rows: RowResolution[];
}

interface WireCommitOut {
  event_id: string;
  event_title: string;
  created_count: number;
  updated_count: number;
  skipped_count: number;
}

export function useCommitAttendanceImport() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: async (input: CommitAttendanceImportInput) => {
      const { data } = await apiClient.post<WireCommitOut>(
        '/api/community/events/attendance-import/commit/',
        {
          event_id: input.eventId,
          event_title: input.eventTitle,
          event_date: input.eventDate,
          rows: input.rows.map((r) => ({
            row_index: r.rowIndex,
            raw_name: r.rawName,
            partiful_status: r.partifulStatus,
            checked_in: r.checkedIn,
            user_id: r.userId,
            skip: r.skip,
          })),
        },
      );
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
    },
  });
}
