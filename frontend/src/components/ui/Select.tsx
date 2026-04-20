import { forwardRef, type SelectHTMLAttributes } from 'react';
import { cn } from '@/utils/cn';

interface Option {
  value: string;
  label: string;
}

interface Props extends Omit<SelectHTMLAttributes<HTMLSelectElement>, 'children'> {
  label: string;
  options: Option[];
  placeholder?: string;
  error?: string | undefined;
}

export const Select = forwardRef<HTMLSelectElement, Props>(function Select(
  { label, options, placeholder, error, className, id, ...rest },
  ref,
) {
  const inputId = id ?? `field-${label.replace(/\s+/g, '-').toLowerCase()}`;
  return (
    <div className="flex flex-col gap-1">
      <label htmlFor={inputId} className="text-foreground text-sm font-medium">
        {label}
      </label>
      <div className="relative">
        <select
          ref={ref}
          id={inputId}
          aria-invalid={error ? true : undefined}
          aria-describedby={error ? `${inputId}-error` : undefined}
          className={cn(
            'border-border-strong bg-surface focus:ring-border h-10 w-full appearance-none rounded-md border pr-9 pl-3 text-sm transition-colors outline-none focus:border-neutral-500 focus:ring-2',
            error && 'border-destructive-border focus:border-red-500 focus:ring-red-100',
            className,
          )}
          {...rest}
        >
          {placeholder ? (
            <option value="" disabled>
              {placeholder}
            </option>
          ) : null}
          {options.map((o) => (
            <option key={o.value} value={o.value}>
              {o.label}
            </option>
          ))}
        </select>
        <svg
          aria-hidden="true"
          viewBox="0 0 20 20"
          className="text-foreground-secondary pointer-events-none absolute inset-y-0 end-3 my-auto h-4 w-4"
          fill="none"
          stroke="currentColor"
          strokeWidth="2"
          strokeLinecap="round"
          strokeLinejoin="round"
        >
          <path d="M6 8l4 4 4-4" />
        </svg>
      </div>
      {error ? (
        <p id={`${inputId}-error`} className="text-destructive text-xs">
          {error}
        </p>
      ) : null}
    </div>
  );
});
