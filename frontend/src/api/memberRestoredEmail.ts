import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query';

import { useAuthStore } from '@/auth/store';

import { apiClient } from './client';
import type { MemberPromotionEmail } from './content';

const URL = '/api/community/member-restored-email/';
const QUERY_KEY = ['member-restored-email'];

interface WireMemberRestoredEmail {
  body: string;
  updated_at: string;
}

function mapMemberRestoredEmail(data: WireMemberRestoredEmail): MemberPromotionEmail {
  return { body: data.body, updatedAt: data.updated_at };
}

export function useMemberRestoredEmail() {
  const isAuthed = useAuthStore((s) => s.status === 'authed');
  return useQuery({
    queryKey: QUERY_KEY,
    queryFn: async () => {
      const { data } = await apiClient.get<WireMemberRestoredEmail>(URL);
      return mapMemberRestoredEmail(data);
    },
    enabled: isAuthed,
  });
}

export function useUpdateMemberRestoredEmail() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: async (body: string) => {
      const { data } = await apiClient.patch<WireMemberRestoredEmail>(URL, { body });
      return mapMemberRestoredEmail(data);
    },
    onSuccess: (template) => {
      qc.setQueryData(QUERY_KEY, template);
    },
  });
}
