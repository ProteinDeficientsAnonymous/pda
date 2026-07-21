import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query';

import { mapEvent, type WireEvent } from '@/api/eventMapper';
import type { components } from '@/api/types.gen';
import type { Event, RsvpInputStatus } from '@/models/event';

import { apiClient } from './client';

export type PublicRsvpIn = components['schemas']['PublicRsvpIn'];
export type PublicRsvpOut = components['schemas']['PublicRsvpOut'];
export type PublicRsvpPhoneStatus = components['schemas']['PublicRsvpPhoneStatus'];
export type PublicRsvpPhoneCheckOut = components['schemas']['PublicRsvpPhoneCheckOut'];
export type ResendManageLinkOut = components['schemas']['ResendManageLinkOut'];
type PublicRsvpManageIn = components['schemas']['PublicRsvpManageIn'];

interface SubmitArgs {
  eventId: string;
  payload: PublicRsvpIn;
}

export function useSubmitPublicRsvp() {
  return useMutation({
    mutationFn: async ({ eventId, payload }: SubmitArgs) => {
      const { data } = await apiClient.post<PublicRsvpOut>(
        `/api/community/public/events/${eventId}/rsvp/`,
        payload,
      );
      return data;
    },
  });
}

interface PhoneCheckArgs {
  eventId: string;
  phoneNumber: string;
}

export function useCheckPublicRsvpPhone() {
  return useMutation({
    mutationFn: async ({ eventId, phoneNumber }: PhoneCheckArgs) => {
      const { data } = await apiClient.post<PublicRsvpPhoneCheckOut>(
        `/api/community/public/events/${eventId}/rsvp-phone-check/`,
        { phone_number: phoneNumber },
      );
      return data;
    },
  });
}

interface ResendArgs {
  phoneNumber: string;
}

export function useResendPublicRsvpManageLink() {
  return useMutation({
    mutationFn: async ({ phoneNumber }: ResendArgs) => {
      const { data } = await apiClient.post<ResendManageLinkOut>(
        '/api/community/public/my-rsvps/resend/',
        { phone_number: phoneNumber, website: '' },
      );
      return data;
    },
  });
}

export interface ManageRsvps {
  user: { name: string; email: string; phoneNumber: string };
  rsvps: { event: Event; status: string; hasPlusOne: boolean }[];
}

interface WireManageOut {
  user: { display_name: string; email: string; phone_number: string };
  rsvps: { event: WireEvent; status: string; has_plus_one: boolean }[];
}

const MANAGE_BASE = '/api/community/public/my-rsvps/';

function manageQueryKey(token: string) {
  return ['public-my-rsvps', token] as const;
}

async function fetchMyRsvps(token: string): Promise<ManageRsvps> {
  const { data } = await apiClient.get<WireManageOut>(MANAGE_BASE, { params: { token } });
  const u = data.user;
  return {
    user: { name: u.display_name, email: u.email, phoneNumber: u.phone_number },
    rsvps: data.rsvps.map((r) => ({
      event: mapEvent(r.event),
      status: r.status,
      hasPlusOne: r.has_plus_one,
    })),
  };
}

export function usePublicMyRsvps(token: string) {
  return useQuery({
    queryKey: manageQueryKey(token),
    queryFn: () => fetchMyRsvps(token),
    enabled: token.length > 0,
    retry: false,
  });
}

interface UpdateArgs {
  eventId: string;
  status: RsvpInputStatus;
  hasPlusOne: boolean;
  comment?: string;
}

function useManageInvalidate(token: string) {
  const queryClient = useQueryClient();
  return () => {
    void queryClient.invalidateQueries({ queryKey: manageQueryKey(token) });
  };
}

export function useUpdatePublicMyRsvp(token: string) {
  return useMutation({
    mutationFn: async ({ eventId, status, hasPlusOne, comment }: UpdateArgs) => {
      const body: PublicRsvpManageIn = {
        status,
        has_plus_one: hasPlusOne,
        comment: comment ?? null,
      };
      const { data } = await apiClient.post<PublicRsvpOut>(`${MANAGE_BASE}${eventId}/`, body, {
        params: { token },
      });
      return data;
    },
    onSuccess: useManageInvalidate(token),
  });
}

export function useCancelPublicMyRsvp(token: string) {
  return useMutation({
    mutationFn: async (eventId: string) => {
      await apiClient.delete(`${MANAGE_BASE}${eventId}/`, { params: { token } });
    },
    onSuccess: useManageInvalidate(token),
  });
}
