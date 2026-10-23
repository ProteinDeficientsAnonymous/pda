import type { EventDescriptionTemplates } from '@/api/eventDescriptionTemplates';
import type { EventFormValues } from '@/api/eventWrites';
import { type EventTag, EventType } from '@/models/event';

export const WALK_TAG_SLUG = 'walk';

const PLACEHOLDER_PATTERN = /\[[^\]a-z]*[A-Z][^\]a-z]*\]/;

export function hasTemplatePlaceholders(description: string): boolean {
  return PLACEHOLDER_PATTERN.test(description);
}

export function walkTagIds(tags: readonly EventTag[] | undefined): string[] {
  return (tags ?? []).filter((t) => t.slug === WALK_TAG_SLUG).map((t) => t.id);
}

// Fills (or swaps/clears) the description from the official templates, but only while the planner hasn't edited it.
export function withOfficialTemplate(
  values: EventFormValues,
  walkIds: readonly string[],
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
  const isWalk = values.tagIds.some((id) => walkIds.includes(id));
  return {
    ...values,
    description: isWalk ? templates.officialWalk : templates.officialNonWalk,
  };
}
