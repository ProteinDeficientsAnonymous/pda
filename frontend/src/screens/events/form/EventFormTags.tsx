import { useEventTags } from '@/api/eventTags';
import type { EventFormValues } from '@/api/eventWrites';

interface Props {
  values: EventFormValues;
  onChange: (patch: Partial<EventFormValues>) => void;
}

export function EventFormTags({ values, onChange }: Props) {
  const { data: tags, isPending, isError } = useEventTags();

  function toggle(id: string) {
    const next = values.tagIds.includes(id)
      ? values.tagIds.filter((t) => t !== id)
      : [...values.tagIds, id];
    onChange({ tagIds: next });
  }

  if (isPending) {
    return <p className="text-foreground-tertiary text-sm">loading tags…</p>;
  }
  if (isError) {
    return <p className="text-foreground-tertiary text-sm">couldn't load tags — try again</p>;
  }
  if (tags.length === 0) {
    return <p className="text-foreground-tertiary text-sm">no tags yet 🌿</p>;
  }

  return (
    <div className="flex flex-col gap-3">
      <p className="text-foreground-secondary text-xs">
        pick tags so people can find this at a glance
      </p>
      <div className="flex flex-wrap gap-2" role="group" aria-label="tags">
        {tags.map((t) => {
          const selected = values.tagIds.includes(t.id);
          return (
            <button
              key={t.id}
              type="button"
              aria-pressed={selected}
              onClick={() => {
                toggle(t.id);
              }}
              className={
                selected
                  ? 'bg-brand-600 text-brand-on inline-flex items-center rounded-full px-3 py-1 text-sm'
                  : 'bg-surface-dim text-foreground-secondary hover:bg-surface-dim/70 inline-flex items-center rounded-full px-3 py-1 text-sm'
              }
            >
              {t.name}
            </button>
          );
        })}
      </div>
    </div>
  );
}
