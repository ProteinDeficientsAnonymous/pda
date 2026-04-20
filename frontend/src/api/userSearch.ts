// Member search — used by co-host picker and invite picker in the event form.

import { useQuery } from '@tanstack/react-query';
import { apiClient } from './client';

export interface MemberSearchResult {
  id: string;
  displayName: string;
  phoneNumber: string;
}

interface Wire {
  id: string;
  display_name: string;
  phone_number: string;
}

export function useUserSearch(term: string) {
  const trimmed = term.trim();
  return useQuery({
    queryKey: ['user-search', trimmed],
    queryFn: async () => {
      const { data } = await apiClient.get<Wire[]>('/api/auth/users/search/', {
        params: { q: trimmed },
      });
      return data.map<MemberSearchResult>((u) => ({
        id: u.id,
        displayName: u.display_name,
        phoneNumber: u.phone_number,
      }));
    },
    enabled: trimmed.length >= 2,
    staleTime: 30_000,
  });
}
