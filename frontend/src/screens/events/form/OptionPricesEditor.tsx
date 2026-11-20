import { TextField } from '@/components/ui/TextField';

interface Props {
  options: readonly string[];
  prices: Readonly<Record<string, string>>;
  onChange: (option: string, dollars: string) => void;
}

export function OptionPricesEditor({ options, prices, onChange }: Props) {
  if (options.length === 0) return null;
  return (
    <fieldset className="flex flex-col gap-2">
      <legend className="text-foreground text-sm font-medium">prices</legend>
      <p className="text-foreground-tertiary text-xs">
        dollars per option — each guest sees the total of what they pick
      </p>
      {options.map((option, index) => (
        <TextField
          key={`${String(index)}-${option}`}
          id={`option-price-${String(index)}`}
          label={`price for ${option}`}
          value={prices[option] ?? ''}
          inputMode="decimal"
          placeholder="0"
          onChange={(e) => {
            onChange(option, e.target.value);
          }}
        />
      ))}
    </fieldset>
  );
}
