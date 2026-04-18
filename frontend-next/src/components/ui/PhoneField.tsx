import PhoneInput, { type Country, type Value } from 'react-phone-number-input';
import 'react-phone-number-input/style.css';
import { cn } from '@/utils/cn';

interface Props {
  label: string;
  value: string;
  onChange: (value: string) => void;
  error?: string | undefined;
  hint?: string | undefined;
  defaultCountry?: Country;
  id?: string;
}

export function PhoneField({
  label,
  value,
  onChange,
  error,
  hint,
  defaultCountry = 'US',
  id,
}: Props) {
  const inputId = id ?? `field-${label.replace(/\s+/g, '-').toLowerCase()}`;
  const describedBy = error ? `${inputId}-error` : hint ? `${inputId}-hint` : undefined;
  return (
    <div className="flex flex-col gap-1">
      <label htmlFor={inputId} className="text-sm font-medium text-neutral-800">
        {label}
      </label>
      <PhoneInput
        id={inputId}
        international
        defaultCountry={defaultCountry}
        value={value as Value}
        onChange={(next) => {
          onChange((next as string | undefined) ?? '');
        }}
        aria-invalid={error ? true : undefined}
        aria-describedby={describedBy}
        numberInputProps={{
          'aria-label': label,
          className: cn(
            'h-10 w-full rounded-md border border-neutral-300 bg-white px-3 text-sm transition-colors outline-none focus:border-neutral-500 focus:ring-2 focus:ring-neutral-200',
            error && 'border-red-500 focus:border-red-500 focus:ring-red-100',
          ),
        }}
        countrySelectProps={{
          'aria-label': 'country',
        }}
        className={cn(
          'PhoneInput flex items-center gap-2',
          '[&_.PhoneInputCountry]:flex [&_.PhoneInputCountry]:items-center [&_.PhoneInputCountry]:gap-1',
          '[&_.PhoneInputCountrySelect]:h-10 [&_.PhoneInputCountrySelect]:rounded-md [&_.PhoneInputCountrySelect]:border [&_.PhoneInputCountrySelect]:border-neutral-300 [&_.PhoneInputCountrySelect]:bg-white [&_.PhoneInputCountrySelect]:px-2 [&_.PhoneInputCountrySelect]:text-sm',
        )}
      />
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
}
