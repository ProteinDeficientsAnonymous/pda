// Tag filter for the calendar — a row of toggle chips. An event matches when it
// carries any selected tag (OR semantics). Renders nothing while tags are
// loading or when the curated set is empty, so the calendar isn't cluttered.

import { useEventTags } from '@/api/eventTags';

interface Props {
  selected: string[];
  onChange: (next: string[]) => void;
}

export function CalendarTagFilter({ selected, onChange }: Props) {
  const { data: tags } = useEventTags();

  if (!tags || tags.length === 0) return null;

  function toggle(id: string) {
    onChange(selected.includes(id) ? selected.filter((t) => t !== id) : [...selected, id]);
  }

  return (
    <div
      className="mb-3 flex flex-wrap items-center justify-center gap-2"
      role="group"
      aria-label="filter by tag"
    >
      {tags.map((t) => {
        const active = selected.includes(t.id);
        return (
          <button
            key={t.id}
            type="button"
            aria-pressed={active}
            onClick={() => {
              toggle(t.id);
            }}
            className={
              active
                ? 'bg-brand-600 text-brand-on inline-flex items-center rounded-full px-3 py-1 text-xs'
                : 'bg-surface-dim text-foreground-secondary hover:bg-surface-dim/70 inline-flex items-center rounded-full px-3 py-1 text-xs'
            }
          >
            {t.name}
          </button>
        );
      })}
      {selected.length > 0 ? (
        <button
          type="button"
          onClick={() => {
            onChange([]);
          }}
          className="text-foreground-tertiary hover:text-brand-700 inline-flex items-center px-2 py-1 text-xs underline"
        >
          clear
        </button>
      ) : null}
    </div>
  );
}
