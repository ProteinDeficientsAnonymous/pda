import { LabelSuffix } from '@/components/ui/LabelSuffix';
import { cn } from '@/utils/cn';

import { FieldError } from './FieldError';

export function StarRating({
  label,
  labelSuffix,
  value,
  labels,
  onChange,
  error,
  readOnly,
}: {
  label: string;
  labelSuffix: string | undefined;
  value: number;
  labels: string[];
  onChange: (n: number) => void;
  error?: string | undefined;
  readOnly?: boolean | undefined;
}) {
  return (
    <fieldset className="flex flex-col gap-2">
      <legend className="text-foreground text-sm font-medium">
        {label}
        {labelSuffix ? <LabelSuffix>{labelSuffix}</LabelSuffix> : null}
      </legend>
      <div role="radiogroup" aria-label={label} className="flex gap-1">
        {[1, 2, 3, 4, 5].map((n) => {
          const filled = n <= value;
          return (
            <button
              key={n}
              type="button"
              role="radio"
              aria-checked={n === value}
              aria-label={labels[n - 1] ?? `${String(n)} star${n === 1 ? '' : 's'}`}
              disabled={readOnly}
              onClick={() => {
                onChange(n);
              }}
              className={cn(
                'text-2xl transition-colors disabled:cursor-not-allowed',
                filled ? 'text-amber-500' : 'text-toggle-off',
              )}
            >
              ★
            </button>
          );
        })}
      </div>
      <FieldError error={error} />
    </fieldset>
  );
}
