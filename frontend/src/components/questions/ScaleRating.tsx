import { LabelSuffix } from '@/components/ui/LabelSuffix';
import { cn } from '@/utils/cn';

import { FieldError } from './FieldError';
import { RATING_SCALE_SIZE, scaleEndLabels, scalePointLabel } from './questionTypeOptions';

const POINTS = Array.from({ length: RATING_SCALE_SIZE }, (_, i) => i + 1);

interface Props {
  label: string;
  labelSuffix: string | undefined;
  value: number;
  endLabels: string[];
  onChange: (n: number) => void;
  error?: string | undefined;
  readOnly?: boolean | undefined;
}

export function ScaleRating({
  label,
  labelSuffix,
  value,
  endLabels,
  onChange,
  error,
  readOnly,
}: Props) {
  const [low, high] = scaleEndLabels(endLabels);

  return (
    <fieldset className="flex flex-col gap-2">
      <legend className="text-foreground text-sm font-medium">
        {label}
        {labelSuffix ? <LabelSuffix>{labelSuffix}</LabelSuffix> : null}
      </legend>
      <div className="flex max-w-sm flex-col gap-1">
        <div role="radiogroup" aria-label={label} className="flex gap-2">
          {POINTS.map((n) => (
            <button
              key={n}
              type="button"
              role="radio"
              aria-checked={n === value}
              aria-label={scalePointLabel(n, endLabels)}
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
        {low || high ? (
          <div aria-hidden="true" className="text-muted flex justify-between gap-4 text-xs">
            <span>{low}</span>
            <span className="text-end">{high}</span>
          </div>
        ) : null}
      </div>
      <FieldError error={error} />
    </fieldset>
  );
}
