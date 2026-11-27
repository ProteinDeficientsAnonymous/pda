import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query';

import { reportError } from '@/utils/errorReporter';

import { apiClient } from './client';
import type { components } from './types.gen';

export type BlastIn = components['schemas']['BlastIn'];
export type BlastPreview = components['schemas']['BlastPreviewOut'];
export type BlastTestResult = components['schemas']['BlastTestOut'];
export type MemberBlast = components['schemas']['BlastOut'];

const ROUTE = '/admin/email-blast';
const BASE = '/api/notifications/email-blasts/';
const BLASTS_KEY = ['member-blasts'];

function useBlastMutation<T>(path: string, action: string, onSuccess?: () => void) {
  return useMutation({
    mutationFn: async (payload: BlastIn): Promise<T> => {
      const { data } = await apiClient.post<T>(path, payload);
      return data;
    },
    onSuccess,
    onError: (err) => {
      void reportError(err, ROUTE, { action });
    },
  });
}

export function useBlastPreview() {
  return useBlastMutation<BlastPreview>(`${BASE}preview/`, 'blast-preview');
}

export function useSendTestBlast() {
  return useBlastMutation<BlastTestResult>(`${BASE}test/`, 'blast-test');
}

export function useSendMemberBlast() {
  const qc = useQueryClient();
  return useBlastMutation<MemberBlast>(BASE, 'blast-send', () => {
    void qc.invalidateQueries({ queryKey: BLASTS_KEY });
  });
}

export function useMemberBlasts() {
  return useQuery({
    queryKey: BLASTS_KEY,
    queryFn: async () => {
      const { data } = await apiClient.get<MemberBlast[]>(BASE);
      return data;
    },
  });
}
