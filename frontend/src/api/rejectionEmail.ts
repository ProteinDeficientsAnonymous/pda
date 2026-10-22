import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query';

import { useAuthStore } from '@/auth/store';

import { apiClient } from './client';

export const RejectionReason = {
  VEGETARIAN: 'vegetarian',
  NOT_VEGAN: 'not_vegan',
  QUESTIONS_NOT_ANSWERED: 'questions_not_answered',
  OTHER: 'other',
} as const;
export type RejectionReason = (typeof RejectionReason)[keyof typeof RejectionReason];

export type PresetRejectionReason = Exclude<RejectionReason, typeof RejectionReason.OTHER>;

export const PRESET_REJECTION_REASONS: PresetRejectionReason[] = [
  RejectionReason.VEGETARIAN,
  RejectionReason.NOT_VEGAN,
  RejectionReason.QUESTIONS_NOT_ANSWERED,
];

export const REJECTION_REASON_LABELS: Record<RejectionReason, string> = {
  [RejectionReason.VEGETARIAN]: 'person is vegetarian',
  [RejectionReason.NOT_VEGAN]: 'person is not vegan (not vegetarian)',
  [RejectionReason.QUESTIONS_NOT_ANSWERED]: 'questions not answered',
  [RejectionReason.OTHER]: 'other',
};

export interface RejectionEmail {
  body: string;
  reasons: Record<PresetRejectionReason, string>;
  updatedAt: string;
}

interface WireRejectionEmail {
  body: string;
  reasons: Record<string, string>;
  updated_at: string;
}

function mapRejectionEmail(data: WireRejectionEmail): RejectionEmail {
  const reasons = Object.fromEntries(
    PRESET_REJECTION_REASONS.map((key) => [key, data.reasons[key] ?? '']),
  ) as Record<PresetRejectionReason, string>;
  return { body: data.body, reasons, updatedAt: data.updated_at };
}

export function useRejectionEmail() {
  const isAuthed = useAuthStore((s) => s.status === 'authed');
  return useQuery({
    queryKey: ['rejection-email'],
    queryFn: async () => {
      const { data } = await apiClient.get<WireRejectionEmail>('/api/community/rejection-email/');
      return mapRejectionEmail(data);
    },
    enabled: isAuthed,
  });
}

export function useUpdateRejectionEmail() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: async (input: Pick<RejectionEmail, 'body' | 'reasons'>) => {
      const { data } = await apiClient.patch<WireRejectionEmail>(
        '/api/community/rejection-email/',
        input,
      );
      return mapRejectionEmail(data);
    },
    onSuccess: (template) => {
      qc.setQueryData(['rejection-email'], template);
    },
  });
}
