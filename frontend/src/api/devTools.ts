import { useMutation, useQueryClient } from '@tanstack/react-query';

import { apiClient } from './client';
import { eventKeys } from './events';

interface CreateDevTestEventsResponse {
  events: { id: string }[];
}

export function useCreateDevTestEvents() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: async (count: number) => {
      const { data } = await apiClient.post<CreateDevTestEventsResponse>(
        '/api/community/dev/test-events/',
        { count },
      );
      return data;
    },
    onSuccess: () => {
      void queryClient.invalidateQueries({ queryKey: eventKeys.all });
    },
  });
}

export function useDeleteDevTestEvents() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: async () => {
      await apiClient.delete('/api/community/dev/test-events/');
    },
    onSuccess: () => {
      void queryClient.invalidateQueries({ queryKey: eventKeys.all });
    },
  });
}
