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

export interface PausePreview {
  events: PauseImpactEvent[];
  strippedRoles: string[];
  clearsWhatsapp: boolean;
}

export function fetchAttendancePausePreview(userId: string): Promise<PausePreview> {
  return fetchPausePreview(`/api/auth/users/${userId}/attendance-pause-preview/`);
}

export function fetchGuidelinesPausePreview(userId: string): Promise<PausePreview> {
  return fetchPausePreview(`/api/auth/users/${userId}/guidelines-pause-preview/`);
}

async function fetchPausePreview(path: string): Promise<PausePreview> {
  const { data } = await apiClient.get<components['schemas']['PausePreviewOut']>(path);
  return {
    events: data.events.map((e) => ({
      id: e.id,
      title: e.title,
      startDatetime: e.start_datetime ? new Date(e.start_datetime) : null,
      role: e.role,
      outcome: e.outcome,
    })),
    strippedRoles: data.stripped_roles,
    clearsWhatsapp: data.clears_whatsapp,
  };
}
