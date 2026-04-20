import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query';
import { apiClient } from './client';

export interface CalendarToken {
  token: string;
  feedUrl: string;
}

interface WireCalendarToken {
  token: string;
  feed_url: string;
}

function mapToken(w: WireCalendarToken): CalendarToken {
  return { token: w.token, feedUrl: w.feed_url };
}

const CALENDAR_TOKEN_KEY = ['calendar', 'token'] as const;

export function useCalendarToken() {
  return useQuery({
    queryKey: CALENDAR_TOKEN_KEY,
    queryFn: async () => {
      const { data } = await apiClient.get<WireCalendarToken>('/api/community/calendar/token/');
      return mapToken(data);
    },
  });
}

export function useRegenerateCalendarToken() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: async () => {
      const { data } = await apiClient.post<WireCalendarToken>('/api/community/calendar/token/');
      return mapToken(data);
    },
    onSuccess: (token) => {
      qc.setQueryData(CALENDAR_TOKEN_KEY, token);
    },
  });
}
