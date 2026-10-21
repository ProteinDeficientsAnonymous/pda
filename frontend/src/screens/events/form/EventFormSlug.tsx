import type { EventFormValues } from '@/api/eventWrites';
import { TextField } from '@/components/ui/TextField';

import { EVENT_SLUG_MAX_LENGTH, toEventSlugInput } from './eventSlug';

interface Props {
  slug: string;
  onChange: (patch: Partial<EventFormValues>) => void;
  error: string | undefined;
}

export function EventFormSlug({ slug, onChange, error }: Props) {
  return (
    <TextField
      label="event url"
      value={slug}
      onChange={(e) => {
        onChange({ slug: toEventSlugInput(e.target.value) });
      }}
      maxLength={EVENT_SLUG_MAX_LENGTH}
      autoCapitalize="none"
      autoCorrect="off"
      spellCheck={false}
      error={error}
      hint={`${window.location.origin}/events/${slug} — old links keep working`}
    />
  );
}
