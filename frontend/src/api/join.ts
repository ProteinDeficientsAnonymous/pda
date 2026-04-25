// Join-request API: fetch the dynamic question list + submit. The static
// fields (display_name, phone_number) are NOT in the question list — the form
// composes them with the server questions.
//
// The submit endpoint has three notable error shapes:
//   400 { detail }                  — validation (bad name, duplicate pending, etc.)
//   409 { detail: 'already_invited' } — phone already matches a user → /login?invited=true

import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query';
import { apiClient } from './client';

export type JoinQuestionType = 'text' | 'select';

export interface JoinQuestion {
  id: string;
  label: string;
  fieldType: JoinQuestionType;
  options: string[];
  required: boolean;
  displayOrder: number;
}

interface WireQuestion {
  id: string;
  label: string;
  field_type: JoinQuestionType;
  options?: string[];
  required?: boolean;
  display_order: number;
}

async function fetchJoinQuestions(): Promise<JoinQuestion[]> {
  const { data } = await apiClient.get<WireQuestion[]>('/api/community/join-form/');
  return data
    .map((q) => ({
      id: q.id,
      label: q.label,
      fieldType: q.field_type,
      options: q.options ?? [],
      required: q.required ?? false,
      displayOrder: q.display_order,
    }))
    .sort((a, b) => a.displayOrder - b.displayOrder);
}

export function useJoinQuestions() {
  return useQuery({ queryKey: ['join-questions'], queryFn: fetchJoinQuestions });
}

export interface SubmitJoinRequestPayload {
  displayName: string;
  phoneNumber: string;
  answers: Record<string, string>;
  website: string;
}

export class AlreadyInvitedError extends Error {
  constructor() {
    super('already_invited');
    this.name = 'AlreadyInvitedError';
  }
}

export function useSubmitJoinRequest() {
  return useMutation({
    mutationFn: async (payload: SubmitJoinRequestPayload) => {
      try {
        await apiClient.post('/api/community/join-request/', {
          display_name: payload.displayName,
          phone_number: payload.phoneNumber,
          answers: payload.answers,
          website: payload.website,
        });
      } catch (err) {
        const status = (err as { response?: { status?: number } }).response?.status;
        if (status === 409) throw new AlreadyInvitedError();
        throw err;
      }
    },
  });
}

// --- phone check -----------------------------------------------------------

export type CheckPhoneStatus = 'member' | 'pending' | 'unknown';

export async function checkPhone(phoneNumber: string): Promise<CheckPhoneStatus> {
  const { data } = await apiClient.post<{ status: CheckPhoneStatus }>(
    '/api/community/check-phone/',
    { phone_number: phoneNumber },
  );
  return data.status;
}

// --- admin ------------------------------------------------------------------

export const JoinRequestStatus = {
  PENDING: 'pending',
  APPROVED: 'approved',
  REJECTED: 'rejected',
} as const;
export type JoinRequestStatus = (typeof JoinRequestStatus)[keyof typeof JoinRequestStatus];

export interface JoinRequestAnswer {
  questionId: string;
  label: string;
  answer: string;
}

export interface JoinRequestSummary {
  id: string;
  displayName: string;
  phoneNumber: string;
  answers: JoinRequestAnswer[];
  submittedAt: string;
  status: JoinRequestStatus;
  userId: string | null;
  previouslyArchived: boolean;
  approvedAt: string | null;
  approvedByName: string | null;
  rejectedAt: string | null;
  rejectedByName: string | null;
  onboardedAt: string | null;
}

interface WireAnswer {
  question_id: string;
  label: string;
  answer: string;
}

interface WireJoinRequest {
  id: string;
  display_name: string;
  phone_number: string;
  answers: WireAnswer[];
  submitted_at: string;
  status: JoinRequestStatus;
  user_id: string | null;
  previously_archived?: boolean;
  approved_at?: string | null;
  approved_by_name?: string | null;
  rejected_at?: string | null;
  rejected_by_name?: string | null;
  onboarded_at?: string | null;
}

function mapJoinRequest(w: WireJoinRequest): JoinRequestSummary {
  return {
    id: w.id,
    displayName: w.display_name,
    phoneNumber: w.phone_number,
    answers: w.answers.map((a) => ({
      questionId: a.question_id,
      label: a.label,
      answer: a.answer,
    })),
    submittedAt: w.submitted_at,
    status: w.status,
    userId: w.user_id,
    previouslyArchived: w.previously_archived ?? false,
    approvedAt: w.approved_at ?? null,
    approvedByName: w.approved_by_name ?? null,
    rejectedAt: w.rejected_at ?? null,
    rejectedByName: w.rejected_by_name ?? null,
    onboardedAt: w.onboarded_at ?? null,
  };
}

export function useJoinRequests() {
  return useQuery({
    queryKey: ['join-requests'],
    queryFn: async () => {
      const { data } = await apiClient.get<WireJoinRequest[]>('/api/community/join-requests/');
      return data.map(mapJoinRequest);
    },
  });
}

// --- join-form question admin -------------------------------------------

export interface JoinQuestionInput {
  label: string;
  fieldType: JoinQuestionType;
  options: string[];
  required: boolean;
}

function fromWire(w: WireQuestion): JoinQuestion {
  return {
    id: w.id,
    label: w.label,
    fieldType: w.field_type,
    options: w.options ?? [],
    required: w.required ?? false,
    displayOrder: w.display_order,
  };
}

export function useCreateJoinQuestion() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: async (input: JoinQuestionInput) => {
      const { data } = await apiClient.post<WireQuestion>('/api/community/join-form/questions/', {
        label: input.label,
        field_type: input.fieldType,
        options: input.options,
        required: input.required,
      });
      return fromWire(data);
    },
    onSuccess: () => {
      void qc.invalidateQueries({ queryKey: ['join-questions'] });
    },
  });
}

export function useUpdateJoinQuestion(questionId: string) {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: async (input: JoinQuestionInput) => {
      // Backend PATCH has PUT semantics — send all four fields every time.
      const { data } = await apiClient.patch<WireQuestion>(
        `/api/community/join-form/questions/${questionId}/`,
        {
          label: input.label,
          field_type: input.fieldType,
          options: input.options,
          required: input.required,
        },
      );
      return fromWire(data);
    },
    onSuccess: () => {
      void qc.invalidateQueries({ queryKey: ['join-questions'] });
    },
  });
}

export function useDeleteJoinQuestion() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: async (questionId: string) => {
      await apiClient.delete(`/api/community/join-form/questions/${questionId}/`);
    },
    onSuccess: () => {
      void qc.invalidateQueries({ queryKey: ['join-questions'] });
    },
  });
}

export function useReorderJoinQuestions() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: async (questionIds: string[]) => {
      const { data } = await apiClient.put<WireQuestion[]>(
        '/api/community/join-form/questions/order/',
        { question_ids: questionIds },
      );
      return data.map(fromWire);
    },
    onSuccess: (ordered) => {
      qc.setQueryData(['join-questions'], ordered);
    },
  });
}

export interface JoinRequestDecision {
  id: string;
  displayName: string;
  phoneNumber: string;
  status: JoinRequestStatus;
  /** Present only when the decision created a brand-new user. */
  magicLinkToken: string | null;
  userId: string | null;
}

interface WireDecision {
  id: string;
  display_name: string;
  phone_number: string;
  status: JoinRequestStatus;
  magic_link_token: string | null;
  user_id: string | null;
}

export function useDecideJoinRequest() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: async (args: {
      id: string;
      status: typeof JoinRequestStatus.APPROVED | typeof JoinRequestStatus.REJECTED;
    }) => {
      const { data } = await apiClient.patch<WireDecision>(
        `/api/community/join-requests/${args.id}/`,
        { status: args.status },
      );
      return {
        id: data.id,
        displayName: data.display_name,
        phoneNumber: data.phone_number,
        status: data.status,
        magicLinkToken: data.magic_link_token,
        userId: data.user_id,
      } satisfies JoinRequestDecision;
    },
    onSuccess: () => {
      void qc.invalidateQueries({ queryKey: ['join-requests'] });
    },
  });
}

export function useUnrejectJoinRequest() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: async (id: string) => {
      await apiClient.patch(`/api/community/join-requests/${id}/unreject/`);
    },
    onSuccess: () => {
      void qc.invalidateQueries({ queryKey: ['join-requests'] });
    },
  });
}

export function useResendMagicLink() {
  return useMutation({
    mutationFn: async (id: string) => {
      const { data } = await apiClient.post<WireDecision>(
        `/api/community/join-requests/${id}/resend-magic-link/`,
      );
      return {
        id: data.id,
        displayName: data.display_name,
        phoneNumber: data.phone_number,
        status: data.status,
        magicLinkToken: data.magic_link_token,
        userId: data.user_id,
      } satisfies JoinRequestDecision;
    },
  });
}
