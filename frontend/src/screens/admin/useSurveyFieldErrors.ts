import { useState } from 'react';

import { getFieldError } from '@/api/apiErrors';

import type { SurveyFormValues } from './SurveyFields';

export function useSurveyFieldErrors() {
  const [slugError, setSlugError] = useState<string | null>(null);
  const [linkedEventError, setLinkedEventError] = useState<string | null>(null);

  return {
    slugError,
    linkedEventError,
    reset() {
      setSlugError(null);
      setLinkedEventError(null);
    },
    clearFor(patch: Partial<SurveyFormValues>) {
      if ('slug' in patch) setSlugError(null);
      if ('linkedEventId' in patch) setLinkedEventError(null);
    },
    capture(err: unknown): boolean {
      const slug = getFieldError(err, 'slug');
      const linkedEvent = getFieldError(err, 'linked_event_id');
      if (slug) setSlugError(slug);
      if (linkedEvent) setLinkedEventError(linkedEvent);
      return Boolean(slug ?? linkedEvent);
    },
  };
}
