import { LabelSuffix } from '@/components/ui/LabelSuffix';
import { cn } from '@/utils/cn';

import { FieldError } from './FieldError';
import { RATING_SCALE_SIZE } from './questionTypeOptions';

const POINTS = Array.from({ length: RATING_SCALE_SIZE }, (_, i) => i + 1);

interface Props {
  label: string;
  labelSuffix: string | undefined;
  value: number;
  onChange: (n: number) => void;
  error?: string | undefined;
  readOnly?: boolean | undefined;
}

export function ScaleRating({ label, labelSuffix, value, onChange, error, readOnly }: Props) {
  return (
    <fieldset className="flex flex-col gap-2">
      <legend className="text-foreground text-sm font-medium">
        {label}
        {labelSuffix ? <LabelSuffix>{labelSuffix}</LabelSuffix> : null}
      </legend>
      <div role="radiogroup" aria-label={label} className="flex max-w-sm gap-2">
        {POINTS.map((n) => (
          <button
            key={n}
            type="button"
            role="radio"
            aria-checked={n === value}
            disabled={readOnly}
            onClick={() => {
              onChange(n);
            }}
            className={cn(
              'h-10 flex-1 rounded-md text-sm font-medium transition-colors disabled:cursor-not-allowed',
              n === value
                ? 'bg-brand-600 text-brand-on'
                : 'border-border-strong text-foreground-secondary hover:bg-background border',
            )}
          >
            {n}
          </button>
        ))}
      </div>
      <FieldError error={error} />
    </fieldset>
  );
}
