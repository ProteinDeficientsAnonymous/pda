import { useState } from 'react';

import { getFieldError } from '@/api/apiErrors';

import type { SurveyFormValues } from './SurveyFields';

export function useSurveyFieldErrors() {
  const [slugError, setSlugError] = useState<string | null>(null);
  const [linkedEventError, setLinkedEventError] = useState<string | null>(null);
  const [feedbackTypeError, setFeedbackTypeError] = useState<string | null>(null);

  return {
    slugError,
    linkedEventError,
    feedbackTypeError,
    reset() {
      setSlugError(null);
      setLinkedEventError(null);
      setFeedbackTypeError(null);
    },
    clearFor(patch: Partial<SurveyFormValues>) {
      if ('slug' in patch) setSlugError(null);
      if ('linkedEventId' in patch) setLinkedEventError(null);
      if ('feedbackEventType' in patch) setFeedbackTypeError(null);
    },
    capture(err: unknown): boolean {
      const slug = getFieldError(err, 'slug');
      const linkedEvent = getFieldError(err, 'linked_event_id');
      if (slug) setSlugError(slug);
      const feedbackType = getFieldError(err, 'feedback_event_type');
      if (linkedEvent) setLinkedEventError(linkedEvent);
      if (feedbackType) setFeedbackTypeError(feedbackType);
      return Boolean(slug ?? linkedEvent ?? feedbackType);
    },
  };
}
