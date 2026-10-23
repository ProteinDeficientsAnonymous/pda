import type { EventDescriptionTemplates } from '@/api/eventDescriptionTemplates';
import type { EventFormValues } from '@/api/eventWrites';
import { EventType } from '@/models/event';

const PLACEHOLDER_PATTERN = /\[[^\]a-z]*[A-Z][^\]a-z]*\]/;

export function hasTemplatePlaceholders(description: string): boolean {
  return PLACEHOLDER_PATTERN.test(description);
}

// Fills (or swaps/clears) the description from the official templates, but only while the planner hasn't edited it.
export function withOfficialTemplate(
  values: EventFormValues,
  templates: EventDescriptionTemplates | undefined,
): EventFormValues {
  if (!templates) return values;
  const { description } = values;
  const untouched =
    description.trim() === '' ||
    description === templates.officialWalk ||
    description === templates.officialNonWalk;
  if (!untouched) return values;

  if (values.eventType !== EventType.Official) {
    return description === '' ? values : { ...values, description: '' };
  }
  return {
    ...values,
    description: values.isWalk ? templates.officialWalk : templates.officialNonWalk,
  };
}
