import type { components } from './types.gen';

/**
 * Full question-type catalog wire values.
 *
 * OpenAPI currently exposes this enum as SurveyQuestionType because survey is
 * the only surface that authors the complete set. Backend's QuestionType is the
 * same catalog; surface subsets (join, later RSVP) extract from it.
 */
export type QuestionType = components['schemas']['SurveyQuestionType'];
