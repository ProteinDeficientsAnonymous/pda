import { useState } from 'react';

import { SegmentedControl } from '@/components/ui/SegmentedControl';
import { TextField } from '@/components/ui/TextField';
import { cn } from '@/utils/cn';

import { labelsEveryScalePoint, RATING_SCALE_SIZE, scaleLabels } from './questionTypeOptions';

type Mode = 'ends' | 'points';

const MODES: { value: Mode; label: string }[] = [
  { value: 'ends', label: 'label the ends' },
  { value: 'points', label: 'label every point' },
];
const POINTS = Array.from({ length: RATING_SCALE_SIZE }, (_, i) => i + 1);
const ENDS = [1, RATING_SCALE_SIZE];
const PLACEHOLDERS: Record<number, string> = { 1: 'e.g. bad', [RATING_SCALE_SIZE]: 'e.g. great' };

interface Props {
  id: string;
  options: string[];
  disabled: boolean;
  onChange: (options: string[]) => void;
  onCommit: (options: string[]) => void;
}

export function ScaleLabelFields({ id, options, disabled, onChange, onCommit }: Props) {
  const [mode, setMode] = useState<Mode>(labelsEveryScalePoint(options) ? 'points' : 'ends');
  const labels = scaleLabels(options);
  const shown = mode === 'points' ? POINTS : ENDS;
  const stored = (next: string[], kind: Mode) =>
    kind === 'points' ? next : ENDS.map((n) => next[n - 1] ?? '');

  return (
    <fieldset disabled={disabled} className="flex flex-col gap-2">
      <SegmentedControl
        name={`${id}-scale-label-mode`}
        ariaLabel="scale labels"
        className="self-start"
        options={MODES}
        value={mode}
        onChange={(next) => {
          setMode(next);
          onCommit(stored(labels, next));
        }}
      />
      <p className="text-muted text-xs">
        optional — words under {mode === 'points' ? 'each point' : 'each end'} of the scale
      </p>
      <div className={cn('grid gap-2', mode === 'points' ? 'grid-cols-1' : 'grid-cols-2')}>
        {shown.map((n) => (
          <TextField
            key={n}
            id={`${id}-scale-label-${String(n)}`}
            label={`label for ${String(n)}`}
            placeholder={PLACEHOLDERS[n]}
            value={labels[n - 1] ?? ''}
            disabled={disabled}
            maxLength={200}
            onChange={(e) => {
              const next = labels.map((label, i) => (i === n - 1 ? e.target.value : label));
              onChange(stored(next, mode));
            }}
            onBlur={() => {
              onCommit(stored(labels, mode));
            }}
          />
        ))}
      </div>
    </fieldset>
  );
}
