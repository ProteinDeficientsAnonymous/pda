// Public survey API — fetch a survey by slug + submit answers.
//
// Answer shape is mixed per question type:
//   - text/textarea/number/yesNo/rating/select/dropdown → string
//   - multiselect → comma-separated string (server parses by split on ",")
//   - datetimePoll → dict { isoOption: "yes" | "maybe" }
//
// Keep these encodings consistent with the Flutter app so data written by
// either client is readable by the other.

import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query';
import { apiClient } from './client';

export type SurveyQuestionType =
  | 'text'
  | 'textarea'
  | 'select'
  | 'multiselect'
  | 'dropdown'
  | 'number'
  | 'yes_no'
  | 'rating'
  | 'datetime_poll';

export interface SurveyQuestion {
  id: string;
  label: string;
  fieldType: SurveyQuestionType;
  options: string[];
  required: boolean;
  displayOrder: number;
}

export interface Survey {
  id: string;
  title: string;
  description: string;
  slug: string;
  visibility: string;
  isActive: boolean;
  oneResponsePerUser: boolean;
  questions: SurveyQuestion[];
  myResponseId: string | null;
  myAnswers: Record<string, { label: string; answer: string | Record<string, string> }> | null;
  pollResult: {
    id: string;
    winningDatetime: string;
    finalizedById: string | null;
    finalizedAt: string;
  } | null;
}

interface WireQuestion {
  id: string;
  label: string;
  field_type: SurveyQuestionType;
  options?: string[];
  required?: boolean;
  display_order: number;
}

interface WireSurvey {
  id: string;
  title: string;
  description?: string;
  slug: string;
  visibility: string;
  is_active: boolean;
  one_response_per_user?: boolean;
  questions?: WireQuestion[];
  my_response_id?: string | null;
  my_answers?: Record<string, { label: string; answer: string | Record<string, string> }> | null;
  poll_result?: {
    id: string;
    winning_datetime: string;
    finalized_by_id: string | null;
    finalized_at: string;
  } | null;
}

interface WireSurveyResponse {
  id: string;
  user_id: string | null;
  user_name: string | null;
  answers: Record<string, string | Record<string, string>>;
  submitted_at: string;
}

function mapSurvey(w: WireSurvey): Survey {
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

export function useSurvey(slug: string | undefined) {
  return useQuery({
    queryKey: ['survey', slug ?? ''],
    queryFn: async () => {
      const { data } = await apiClient.get<WireSurvey>(
        `/api/community/surveys/view/${slug ?? ''}/`,
      );
      return mapSurvey(data);
    },
    enabled: Boolean(slug),
  });
}

export type AnswerValue = string | Record<string, string>;

export function useSubmitSurvey(slug: string) {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: async (answers: Record<string, AnswerValue>) => {
      const { data } = await apiClient.post<WireSurveyResponse>(
        `/api/community/surveys/view/${slug}/respond/`,
        { answers },
      );
      return data;
    },
    onSuccess: () => {
      void qc.invalidateQueries({ queryKey: ['survey', slug] });
    },
  });
}
