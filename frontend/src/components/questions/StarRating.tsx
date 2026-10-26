import { LabelSuffix } from '@/components/ui/LabelSuffix';
import { cn } from '@/utils/cn';

import { FieldError } from './FieldError';
import { RATING_SCALE_SIZE } from './questionTypeOptions';

const STARS = Array.from({ length: RATING_SCALE_SIZE }, (_, i) => i + 1);

interface Props {
  label: string;
  labelSuffix: string | undefined;
  value: number;
  onChange: (n: number) => void;
  error?: string | undefined;
  readOnly?: boolean | undefined;
}

export function StarRating({ label, labelSuffix, value, onChange, error, readOnly }: Props) {
  return (
    <fieldset className="flex flex-col gap-2">
      <legend className="text-foreground text-sm font-medium">
        {label}
        {labelSuffix ? <LabelSuffix>{labelSuffix}</LabelSuffix> : null}
      </legend>
      <div role="radiogroup" aria-label={label} className="flex gap-1">
        {STARS.map((n) => (
          <button
            key={n}
            type="button"
            role="radio"
            aria-checked={n === value}
            aria-label={`${String(n)} star${n === 1 ? '' : 's'}`}
            disabled={readOnly}
            onClick={() => {
              onChange(n);
            }}
            className={cn(
              'text-2xl transition-colors disabled:cursor-not-allowed',
              n <= value ? 'text-amber-500' : 'text-toggle-off',
            )}
          >
            <span aria-hidden="true">★</span>
          </button>
        ))}
      </div>
      <FieldError error={error} />
    </fieldset>
  );
}
