import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query';

import { useAuthStore } from '@/auth/store';

import { apiClient } from './client';
import { mapMemberPromotionEmail, type WireMemberPromotionEmail } from './content';

const URL = '/api/community/member-restored-email/';
const QUERY_KEY = ['member-restored-email'];

export function useMemberRestoredEmail() {
  const isAuthed = useAuthStore((s) => s.status === 'authed');
  return useQuery({
    queryKey: QUERY_KEY,
    queryFn: async () => {
      const { data } = await apiClient.get<WireMemberPromotionEmail>(URL);
      return mapMemberPromotionEmail(data);
    },
    enabled: isAuthed,
  });
}

export function useUpdateMemberRestoredEmail() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: async (body: string) => {
      const { data } = await apiClient.patch<WireMemberPromotionEmail>(URL, { body });
      return mapMemberPromotionEmail(data);
    },
    onSuccess: (template) => {
      qc.setQueryData(QUERY_KEY, template);
    },
  });
}
