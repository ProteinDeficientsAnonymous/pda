import type { SurveySummary } from '@/api/surveyAdmin';

export type SurveyStatus = 'active' | 'scheduled' | 'capped' | 'closed';

type StatusInput = Pick<
  SurveySummary,
  'isActive' | 'opensAt' | 'closesAt' | 'maxResponses' | 'responseCount'
>;

export function surveyStatus(survey: StatusInput, now: Date = new Date()): SurveyStatus {
  if (!survey.isActive) return 'closed';
  if (survey.closesAt && now >= new Date(survey.closesAt)) return 'closed';
  if (survey.opensAt && now < new Date(survey.opensAt)) return 'scheduled';
  if (survey.maxResponses !== null && survey.responseCount >= survey.maxResponses) return 'capped';
  return 'active';
}
