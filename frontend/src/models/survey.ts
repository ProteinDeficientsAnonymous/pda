export type SurveyStatus = 'active' | 'scheduled' | 'capped' | 'closed';

export interface SurveyScheduleFields {
  isActive: boolean;
  opensAt: string | null;
  closesAt: string | null;
  maxResponses: number | null;
  responseCount: number;
}

interface Options {
  now?: Date;
  /** Mirrors the backend's check_cap — a user editing their own response is exempt. */
  checkCap?: boolean;
}

export function surveyStatus(
  survey: SurveyScheduleFields,
  { now = new Date(), checkCap = true }: Options = {},
): SurveyStatus {
  if (!survey.isActive) return 'closed';
  if (survey.closesAt && now >= new Date(survey.closesAt)) return 'closed';
  if (survey.opensAt && now < new Date(survey.opensAt)) return 'scheduled';
  if (checkCap && survey.maxResponses !== null && survey.responseCount >= survey.maxResponses) {
    return 'capped';
  }
  return 'active';
}

export function surveyVisibilityLabel(visibility: string): string {
  return visibility.replaceAll('_', ' ');
}

export const DEFAULT_THANK_YOU_MESSAGE = 'thanks for filling out our survey!';

export function thankYouMessage(confirmationMessage: string): string {
  return confirmationMessage.trim() ? confirmationMessage.toLowerCase() : DEFAULT_THANK_YOU_MESSAGE;
}
