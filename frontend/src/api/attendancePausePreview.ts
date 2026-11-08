import { apiClient } from './client';
import type { components } from './types.gen';

export type PauseRole = components['schemas']['PauseRole'];
export type PauseOutcome = components['schemas']['PauseOutcome'];

export interface PauseImpactEvent {
  id: string;
  title: string;
  startDatetime: Date | null;
  role: PauseRole;
  outcome: PauseOutcome;
}

export async function fetchAttendancePausePreview(userId: string): Promise<PauseImpactEvent[]> {
  const { data } = await apiClient.get<components['schemas']['AttendancePausePreviewOut']>(
    `/api/auth/users/${userId}/attendance-pause-preview/`,
  );
  return data.events.map((e) => ({
    id: e.id,
    title: e.title,
    startDatetime: e.start_datetime ? new Date(e.start_datetime) : null,
    role: e.role,
    outcome: e.outcome,
  }));
}
