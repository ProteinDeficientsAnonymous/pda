import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query';

import { OfficialKind } from '@/models/event';

import { apiClient } from './client';
import { invalidateEventDetail } from './events';

export interface SpeechTemplate {
  sharedPm: string;
  walkPm: string;
  restaurantPm: string;
  openRoles: string[];
  updatedAt: string;
}

export interface SpeechTemplateUpdate {
  sharedPm?: string;
  walkPm?: string;
  restaurantPm?: string;
  openRoles?: string[];
}

interface WireSpeechTemplate {
  shared_pm: string;
  walk_pm: string;
  restaurant_pm: string;
  open_roles: string[];
  updated_at: string;
}

const TEMPLATE_KEY = ['speech-template'] as const;
const TEMPLATE_URL = '/api/community/speech-template/';

function mapTemplate(data: WireSpeechTemplate): SpeechTemplate {
  return {
    sharedPm: data.shared_pm,
    walkPm: data.walk_pm,
    restaurantPm: data.restaurant_pm,
    openRoles: data.open_roles,
    updatedAt: data.updated_at,
  };
}

export function useSpeechTemplate() {
  return useQuery({
    queryKey: TEMPLATE_KEY,
    queryFn: async () => {
      const { data } = await apiClient.get<WireSpeechTemplate>(TEMPLATE_URL);
      return mapTemplate(data);
    },
  });
}

export function useUpdateSpeechTemplate() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: async (patch: SpeechTemplateUpdate) => {
      const body: Record<string, string | string[]> = {};
      if (patch.sharedPm !== undefined) body.shared_pm = patch.sharedPm;
      if (patch.walkPm !== undefined) body.walk_pm = patch.walkPm;
      if (patch.restaurantPm !== undefined) body.restaurant_pm = patch.restaurantPm;
      if (patch.openRoles !== undefined) body.open_roles = patch.openRoles;
      const { data } = await apiClient.patch<WireSpeechTemplate>(TEMPLATE_URL, body);
      return mapTemplate(data);
    },
    onSuccess: (template) => {
      qc.setQueryData(TEMPLATE_KEY, template);
    },
  });
}

export type SpeechValues = Record<string, string | string[]>;

export interface EventSpeech {
  eventTitle: string;
  officialKind: OfficialKind | null;
  saved: boolean;
  values: SpeechValues;
  html: string;
  updatedAt: string | null;
  updatedByName: string | null;
}

export interface EventSpeechSave {
  officialKind?: OfficialKind;
  values: SpeechValues;
}

interface WireEventSpeech {
  event_title: string;
  official_kind: string | null;
  saved: boolean;
  values: SpeechValues;
  html: string;
  updated_at: string | null;
  updated_by_name: string | null;
}

const speechKey = (eventId: string) => ['event-speech', eventId] as const;
const speechUrl = (eventId: string) => `/api/community/events/${eventId}/speech/`;

function mapSpeech(data: WireEventSpeech): EventSpeech {
  const kind = Object.values(OfficialKind).find((k) => k === data.official_kind) ?? null;
  return {
    eventTitle: data.event_title,
    officialKind: kind,
    saved: data.saved,
    values: data.values,
    html: data.html,
    updatedAt: data.updated_at,
    updatedByName: data.updated_by_name,
  };
}

export function useEventSpeech(eventId: string | undefined) {
  return useQuery({
    queryKey: speechKey(eventId ?? ''),
    enabled: !!eventId,
    retry: false,
    queryFn: async () => {
      const { data } = await apiClient.get<WireEventSpeech>(speechUrl(eventId ?? ''));
      return mapSpeech(data);
    },
  });
}

export function useSaveEventSpeech(eventId: string) {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: async (input: EventSpeechSave) => {
      const body: { values: SpeechValues; official_kind?: string } = { values: input.values };
      if (input.officialKind) body.official_kind = input.officialKind;
      const { data } = await apiClient.put<WireEventSpeech>(speechUrl(eventId), body);
      return mapSpeech(data);
    },
    onSuccess: (speech) => {
      qc.setQueryData(speechKey(eventId), speech);
      invalidateEventDetail(qc, eventId);
    },
  });
}
