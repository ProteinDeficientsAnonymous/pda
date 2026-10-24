import { LabelSuffix } from '@/components/ui/LabelSuffix';
import { cn } from '@/utils/cn';

import { FieldError } from './FieldError';
import { ratingLabelSlots } from './questionTypeOptions';

interface Props {
  label: string;
  labelSuffix: string | undefined;
  value: number;
  labels: string[];
  onChange: (n: number) => void;
  error?: string | undefined;
  readOnly?: boolean | undefined;
}

export function StarRating({
  label,
  labelSuffix,
  value,
  labels,
  onChange,
  error,
  readOnly,
}: Props) {
  const slots = ratingLabelSlots(labels).map((l) => l.trim());
  const labeled = slots.some(Boolean);

  return (
    <fieldset className="flex flex-col gap-2">
      <legend className="text-foreground text-sm font-medium">
        {label}
        {labelSuffix ? <LabelSuffix>{labelSuffix}</LabelSuffix> : null}
      </legend>
      <div
        role="radiogroup"
        aria-label={label}
        className={cn('flex gap-1', labeled && 'flex-col items-start')}
      >
        {slots.map((starLabel, i) => {
          const n = i + 1;
          return (
            <button
              key={n}
              type="button"
              role="radio"
              aria-checked={n === value}
              aria-label={starLabel || `${String(n)} star${n === 1 ? '' : 's'}`}
              disabled={readOnly}
              onClick={() => {
                onChange(n);
              }}
              className="flex items-center gap-2 text-start disabled:cursor-not-allowed"
            >
              <span
                aria-hidden="true"
                className={cn(
                  'text-2xl transition-colors',
                  n <= value ? 'text-amber-500' : 'text-toggle-off',
                )}
              >
                ★
              </span>
              {labeled && starLabel ? (
                <span
                  aria-hidden="true"
                  className={cn('text-sm', n === value ? 'text-foreground' : 'text-muted')}
                >
                  {starLabel}
                </span>
              ) : null}
            </button>
          );
        })}
      </div>
      <FieldError error={error} />
    </fieldset>
  );
}
