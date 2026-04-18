import { forwardRef, type InputHTMLAttributes, type ReactNode } from 'react';
import { cn } from '@/utils/cn';

interface Props extends InputHTMLAttributes<HTMLInputElement> {
  label: string;
  error?: string | undefined;
  hint?: string | undefined;
  rightAdornment?: ReactNode;
}

export const TextField = forwardRef<HTMLInputElement, Props>(function TextField(
  { label, error, hint, rightAdornment, className, id, ...rest },
  ref,
) {
  const inputId = id ?? `field-${label.replace(/\s+/g, '-').toLowerCase()}`;
  const describedBy = error ? `${inputId}-error` : hint ? `${inputId}-hint` : undefined;
  return (
    <div className="flex flex-col gap-1">
      <label htmlFor={inputId} className="text-sm font-medium text-neutral-800">
        {label}
      </label>
      <div className="relative">
        <input
          ref={ref}
          id={inputId}
          aria-invalid={error ? true : undefined}
          aria-describedby={describedBy}
          className={cn(
            'focus:border-brand-500 focus:ring-brand-200 h-10 w-full rounded-md border border-neutral-300 bg-white px-3 text-sm transition-colors outline-none focus:ring-2',
            error && 'border-red-500 focus:border-red-500 focus:ring-red-100',
            rightAdornment && 'pr-10',
            className,
          )}
          {...rest}
        />
        {rightAdornment ? (
          <div className="absolute inset-y-0 right-0 flex items-center pr-2">{rightAdornment}</div>
        ) : null}
      </div>
      {error ? (
        <p id={`${inputId}-error`} className="text-xs text-red-600">
          {error}
        </p>
      ) : hint ? (
        <p id={`${inputId}-hint`} className="text-xs text-neutral-500">
          {hint}
        </p>
      ) : null}
    </div>
  );
});
