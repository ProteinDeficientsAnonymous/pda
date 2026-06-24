// Read-only display of an event's tags as a row of neutral chips.
// Neutral styling (no color-coding) keeps it color-blind safe — the tag name
// itself carries the meaning. Renders nothing when there are no tags.

import type { EventTag } from '@/models/event';

interface Props {
  tags: EventTag[];
  className?: string;
}

export function EventTagChips({ tags, className }: Props) {
  if (tags.length === 0) return null;
  return (
    <ul className={`flex flex-wrap gap-2 ${className ?? ''}`} aria-label="tags">
      {tags.map((t) => (
        <li
          key={t.id}
          className="bg-surface-dim text-foreground-secondary inline-flex items-center rounded-full px-2 py-1 text-xs"
        >
          {t.name}
        </li>
      ))}
    </ul>
  );
}
