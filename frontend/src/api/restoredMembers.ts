import { useQuery } from '@tanstack/react-query';

import { apiClient } from './client';
import type { components } from './types.gen';

export type RestoredMember = components['schemas']['RestoredMemberOut'];

// Nested under join-requests so the whatsapp toggle's invalidation refreshes it too.
export function useRestoredMembers() {
  return useQuery({
    queryKey: ['join-requests', 'restored'],
    queryFn: async () => {
      const { data } = await apiClient.get<RestoredMember[]>('/api/auth/users/restored/');
      return data;
    },
  });
}
