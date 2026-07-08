// Host-only group-text recipients (see #500).
//
// GET /text-recipients/ returns 403 for non-hosts, so callers must gate the
// `enabled` flag on host status to avoid noisy error toasts. Phones live only
// on this endpoint — they are not on the shared event payload.

import { useQuery } from '@tanstack/react-query';

import { apiClient } from './client';

export interface TextRecipients {
  attending: string[];
  maybe: string[];
  cantGo: string[];
  waitlisted: string[];
  invited: string[];
}

interface WireTextRecipients {
  attending: string[];
  maybe: string[];
  cant_go: string[];
  waitlisted: string[];
  invited: string[];
}

function mapRecipients(w: WireTextRecipients): TextRecipients {
  return {
    attending: w.attending,
    maybe: w.maybe,
    cantGo: w.cant_go,
    waitlisted: w.waitlisted,
    invited: w.invited,
  };
}

export const textRecipientsKeys = {
  detail: (eventId: string) => ['text-recipients', eventId] as const,
};

export function useTextRecipients(eventId: string | undefined, enabled: boolean) {
  const id = eventId ?? '';
  return useQuery({
    queryKey: textRecipientsKeys.detail(id),
    queryFn: async () => {
      const { data } = await apiClient.get<WireTextRecipients>(
        `/api/community/events/${id}/text-recipients/`,
      );
      return mapRecipients(data);
    },
    enabled: Boolean(eventId) && enabled,
  });
}
