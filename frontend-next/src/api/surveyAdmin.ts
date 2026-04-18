// Survey admin API: list/create/edit/delete surveys, CRUD + reorder on
// their questions, and fetch responses. All endpoints require
// manage_surveys; finalize-poll uses a looser permission check on the
// backend (organizer/co-host/etc.).

import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query';
import { apiClient } from './client';
import type { SurveyQuestion, SurveyQuestionType } from './surveys';

export interface SurveySummary {
  id: string;
  title: string;
  slug: string;
  visibility: string;
  isActive: boolean;
  linkedEventId: string | null;
  createdAt: string;
  responseCount: number;
}

interface WireSummary {
  id: string;
  title: string;
  slug: string;
  visibility: string;
  is_active: boolean;
  linked_event_id: string | null;
  created_at: string;
  response_count: number;
}

function mapSummary(w: WireSummary): SurveySummary {
  return {
    id: w.id,
    title: w.title,
    slug: w.slug,
    visibility: w.visibility,
    isActive: w.is_active,
    linkedEventId: w.linked_event_id,
    createdAt: w.created_at,
    responseCount: w.response_count,
  };
}

export function useAdminSurveys() {
  return useQuery({
    queryKey: ['surveys', 'admin'],
    queryFn: async () => {
      const { data } = await apiClient.get<WireSummary[]>('/api/community/surveys/admin/');
      return data.map(mapSummary);
    },
  });
}

// Admin view of a single survey — mapped via existing Survey shape from
// surveys.ts. We import mapSurvey indirectly by reusing the wire type.
import type { Survey as PublicSurvey } from './surveys';

interface WireSurveyFull {
  id: string;
  title: string;
  description?: string;
  slug: string;
  visibility: string;
  is_active: boolean;
  one_response_per_user?: boolean;
  questions?: {
    id: string;
    label: string;
    field_type: SurveyQuestionType;
    options?: string[];
    required?: boolean;
    display_order: number;
  }[];
  my_response_id?: string | null;
  my_answers?: Record<string, { label: string; answer: string | Record<string, string> }> | null;
  poll_result?: {
    id: string;
    winning_datetime: string;
    finalized_by_id: string | null;
    finalized_at: string;
  } | null;
}

function mapSurveyFull(w: WireSurveyFull): PublicSurvey {
  return {
    id: w.id,
    title: w.title,
    description: w.description ?? '',
    slug: w.slug,
    visibility: w.visibility,
    isActive: w.is_active,
    oneResponsePerUser: w.one_response_per_user ?? false,
    questions: (w.questions ?? [])
      .map((q) => ({
        id: q.id,
        label: q.label,
        fieldType: q.field_type,
        options: q.options ?? [],
        required: q.required ?? false,
        displayOrder: q.display_order,
      }))
      .sort((a, b) => a.displayOrder - b.displayOrder),
    myResponseId: w.my_response_id ?? null,
    myAnswers: w.my_answers ?? null,
    pollResult: w.poll_result
      ? {
          id: w.poll_result.id,
          winningDatetime: w.poll_result.winning_datetime,
          finalizedById: w.poll_result.finalized_by_id,
          finalizedAt: w.poll_result.finalized_at,
        }
      : null,
  };
}

export function useAdminSurvey(id: string | undefined) {
  return useQuery({
    queryKey: ['surveys', 'admin', id ?? ''],
    queryFn: async () => {
      const { data } = await apiClient.get<WireSurveyFull>(
        `/api/community/surveys/${id ?? ''}/admin/`,
      );
      return mapSurveyFull(data);
    },
    enabled: Boolean(id),
  });
}

export interface SurveyInput {
  title: string;
  description: string;
  slug: string;
  visibility: string;
  isActive: boolean;
  oneResponsePerUser: boolean;
  linkedEventId: string | null;
}

export function useCreateSurvey() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: async (input: SurveyInput) => {
      const { data } = await apiClient.post<WireSurveyFull>('/api/community/surveys/', {
        title: input.title,
        description: input.description,
        slug: input.slug,
        visibility: input.visibility,
        is_active: input.isActive,
        one_response_per_user: input.oneResponsePerUser,
        linked_event_id: input.linkedEventId,
      });
      return mapSurveyFull(data);
    },
    onSuccess: () => {
      void qc.invalidateQueries({ queryKey: ['surveys', 'admin'] });
    },
  });
}

export function useUpdateSurvey(surveyId: string) {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: async (patch: Partial<SurveyInput>) => {
      const body: Record<string, unknown> = {};
      if (patch.title !== undefined) body.title = patch.title;
      if (patch.description !== undefined) body.description = patch.description;
      if (patch.slug !== undefined) body.slug = patch.slug;
      if (patch.visibility !== undefined) body.visibility = patch.visibility;
      if (patch.isActive !== undefined) body.is_active = patch.isActive;
      if (patch.oneResponsePerUser !== undefined)
        body.one_response_per_user = patch.oneResponsePerUser;
      if (patch.linkedEventId !== undefined) body.linked_event_id = patch.linkedEventId;
      const { data } = await apiClient.patch<WireSurveyFull>(
        `/api/community/surveys/${surveyId}/`,
        body,
      );
      return mapSurveyFull(data);
    },
    onSuccess: (survey) => {
      qc.setQueryData(['surveys', 'admin', surveyId], survey);
      void qc.invalidateQueries({ queryKey: ['surveys', 'admin'] });
    },
  });
}

export function useDeleteSurvey() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: async (surveyId: string) => {
      await apiClient.delete(`/api/community/surveys/${surveyId}/`);
    },
    onSuccess: () => {
      void qc.invalidateQueries({ queryKey: ['surveys', 'admin'] });
    },
  });
}

export interface SurveyQuestionInput {
  label: string;
  fieldType: SurveyQuestionType;
  options: string[];
  required: boolean;
}

export function useCreateSurveyQuestion(surveyId: string) {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: async (input: SurveyQuestionInput) => {
      const { data } = await apiClient.post<SurveyQuestion>(
        `/api/community/surveys/${surveyId}/questions/`,
        {
          label: input.label,
          field_type: input.fieldType,
          options: input.options,
          required: input.required,
        },
      );
      return data;
    },
    onSuccess: () => {
      void qc.invalidateQueries({ queryKey: ['surveys', 'admin', surveyId] });
    },
  });
}

export function useUpdateSurveyQuestion(surveyId: string, questionId: string) {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: async (input: SurveyQuestionInput) => {
      // PATCH has PUT semantics — always send all four fields.
      const { data } = await apiClient.patch<SurveyQuestion>(
        `/api/community/surveys/${surveyId}/questions/${questionId}/`,
        {
          label: input.label,
          field_type: input.fieldType,
          options: input.options,
          required: input.required,
        },
      );
      return data;
    },
    onSuccess: () => {
      void qc.invalidateQueries({ queryKey: ['surveys', 'admin', surveyId] });
    },
  });
}

export function useDeleteSurveyQuestion(surveyId: string) {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: async (questionId: string) => {
      await apiClient.delete(`/api/community/surveys/${surveyId}/questions/${questionId}/`);
    },
    onSuccess: () => {
      void qc.invalidateQueries({ queryKey: ['surveys', 'admin', surveyId] });
    },
  });
}

export function useReorderSurveyQuestions(surveyId: string) {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: async (questionIds: string[]) => {
      await apiClient.put(`/api/community/surveys/${surveyId}/questions/order/`, {
        question_ids: questionIds,
      });
    },
    onSuccess: () => {
      void qc.invalidateQueries({ queryKey: ['surveys', 'admin', surveyId] });
    },
  });
}

// --- responses -----------------------------------------------------------

export interface SurveyResponseAdmin {
  id: string;
  userId: string | null;
  userName: string | null;
  answers: Record<string, unknown>;
  submittedAt: string;
}

interface WireResponse {
  id: string;
  user_id: string | null;
  user_name: string | null;
  answers: Record<string, unknown>;
  submitted_at: string;
}

export function useSurveyResponses(surveyId: string | undefined) {
  return useQuery({
    queryKey: ['surveys', 'admin', surveyId ?? '', 'responses'],
    queryFn: async () => {
      const { data } = await apiClient.get<WireResponse[]>(
        `/api/community/surveys/${surveyId ?? ''}/responses/`,
      );
      return data.map<SurveyResponseAdmin>((r) => ({
        id: r.id,
        userId: r.user_id,
        userName: r.user_name,
        answers: r.answers,
        submittedAt: r.submitted_at,
      }));
    },
    enabled: Boolean(surveyId),
  });
}

// Re-export survey types for convenience so admin screens don't need to
// import from two places.
export type { Survey, SurveyQuestion, SurveyQuestionType } from './surveys';
