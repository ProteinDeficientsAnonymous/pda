import type { EventDescriptionTemplates } from '@/api/eventDescriptionTemplates';
import type { EventFormValues } from '@/api/eventWrites';
import { EventFormat, EventType } from '@/models/event';

const PLACEHOLDER_PATTERN = /\[[^\]a-z]*[A-Z][^\]a-z]*\]/;

export function hasTemplatePlaceholders(description: string): boolean {
  return PLACEHOLDER_PATTERN.test(description);
}

// Fills (or swaps/clears) the description from the official/club templates, but only while the planner hasn't edited it.
export function withDescriptionTemplate(
  values: EventFormValues,
  templates: EventDescriptionTemplates | undefined,
): EventFormValues {
  if (!templates) return values;
  const { description } = values;
  const untouched =
    description.trim() === '' ||
    description === templates.officialWalk ||
    description === templates.officialNonWalk ||
    description === templates.club;
  if (!untouched) return values;

  const template = templateFor(values, templates);
  if (template === null) {
    return description === '' ? values : { ...values, description: '' };
  }
  return { ...values, description: template };
}

function templateFor(values: EventFormValues, templates: EventDescriptionTemplates): string | null {
  if (values.eventType === EventType.Club) return templates.club;
  if (values.eventType !== EventType.Official) return null;
  return values.eventFormat === EventFormat.Walk
    ? templates.officialWalk
    : templates.officialNonWalk;
}
