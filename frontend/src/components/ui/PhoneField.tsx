import PhoneInput, { type Country, type Value } from 'react-phone-number-input';
import flags from 'react-phone-number-input/flags';
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
      <label htmlFor={inputId} className="text-sm font-medium text-foreground">
        {label}
      </label>
      <PhoneInput
        id={inputId}
        international
        flags={flags}
        defaultCountry={defaultCountry}
        countryCallingCodeEditable={false}
        value={value as Value}
        onChange={(next) => {
          onChange((next as string | undefined) ?? '');
        }}
        aria-invalid={error ? true : undefined}
        aria-describedby={describedBy}
        numberInputProps={{
          'aria-label': label,
          className: cn(
            'h-10 w-full rounded-md border border-border-strong bg-surface px-3 text-sm transition-colors outline-none focus:border-brand-500 focus:ring-2 focus:ring-brand-200',
            error && 'border-destructive-border focus:border-red-500 focus:ring-red-100',
          ),
        }}
        countrySelectProps={{
          'aria-label': 'country',
        }}
        style={
          {
            '--PhoneInput-color--focus': 'var(--color-brand-600)',
          } as React.CSSProperties
        }
        className={cn(
          'PhoneInput flex items-center gap-2',
          '[&_.PhoneInputCountry]:relative [&_.PhoneInputCountry]:flex [&_.PhoneInputCountry]:h-10 [&_.PhoneInputCountry]:items-center [&_.PhoneInputCountry]:gap-1 [&_.PhoneInputCountry]:rounded-md [&_.PhoneInputCountry]:border [&_.PhoneInputCountry]:border-border-strong [&_.PhoneInputCountry]:bg-surface [&_.PhoneInputCountry]:px-2',
          '[&_.PhoneInputCountryIcon]:h-5 [&_.PhoneInputCountryIcon]:w-7 [&_.PhoneInputCountryIcon]:overflow-hidden [&_.PhoneInputCountryIcon]:rounded-[3px] [&_.PhoneInputCountryIcon]:shadow-none',
          '[&_.PhoneInputCountryIcon--border]:shadow-none [&_.PhoneInputCountryIcon--border]:ring-0',
          '[&_.PhoneInputCountryIconImg]:h-full [&_.PhoneInputCountryIconImg]:w-full [&_.PhoneInputCountryIconImg]:object-cover',
          '[&_.PhoneInputCountrySelect]:absolute [&_.PhoneInputCountrySelect]:inset-0 [&_.PhoneInputCountrySelect]:h-full [&_.PhoneInputCountrySelect]:w-full [&_.PhoneInputCountrySelect]:cursor-pointer [&_.PhoneInputCountrySelect]:opacity-0',
          '[&_.PhoneInputCountrySelectArrow]:ml-1 [&_.PhoneInputCountrySelectArrow]:text-foreground-tertiary [&_.PhoneInputCountrySelectArrow]:opacity-60',
        )}
      />
      {error ? (
        <p id={`${inputId}-error`} className="text-xs text-destructive">
          {error}
        </p>
      ) : hint ? (
        <p id={`${inputId}-hint`} className="text-xs text-muted">
          {hint}
        </p>
      ) : null}
    </div>
  );
}
