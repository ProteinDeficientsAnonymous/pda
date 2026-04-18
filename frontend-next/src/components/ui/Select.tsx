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
      <label htmlFor={inputId} className="text-sm font-medium text-neutral-800">
        {label}
      </label>
      <select
        ref={ref}
        id={inputId}
        aria-invalid={error ? true : undefined}
        aria-describedby={error ? `${inputId}-error` : undefined}
        className={cn(
          'h-10 rounded-md border border-neutral-300 bg-white px-3 text-sm transition-colors outline-none focus:border-neutral-500 focus:ring-2 focus:ring-neutral-200',
          error && 'border-red-500 focus:border-red-500 focus:ring-red-100',
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
      {error ? (
        <p id={`${inputId}-error`} className="text-xs text-red-600">
          {error}
        </p>
      ) : null}
    </div>
  );
});
