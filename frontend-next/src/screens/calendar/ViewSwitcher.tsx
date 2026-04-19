// Pill-style segmented control for the 4 calendar views. Replaces Flutter's
// SegmentedButton. Keyboard + screen-reader accessible via <input type="radio">.

import { cn } from '@/utils/cn';
import type { View } from 'react-big-calendar';

interface Props {
  value: View;
  onChange: (view: View) => void;
}

const VIEWS: { value: View; label: string }[] = [
  { value: 'month', label: 'month' },
  { value: 'week', label: 'week' },
  { value: 'day', label: 'day' },
  { value: 'agenda', label: 'list' },
];

export function ViewSwitcher({ value, onChange }: Props) {
  return (
    <div
      role="radiogroup"
      aria-label="calendar view"
      className="inline-flex rounded-md border border-neutral-300 bg-white p-0.5"
    >
      {VIEWS.map((v) => {
        const active = v.value === value;
        return (
          <label
            key={v.value}
            className={cn(
              'inline-flex h-8 cursor-pointer items-center rounded px-3 text-sm transition-colors',
              active ? 'bg-brand-600 text-white' : 'text-neutral-700 hover:bg-neutral-100',
            )}
          >
            <input
              type="radio"
              name="calendar-view"
              value={v.value}
              checked={active}
              onChange={() => {
                onChange(v.value);
              }}
              className="sr-only"
            />
            {v.label}
          </label>
        );
      })}
    </div>
  );
}
