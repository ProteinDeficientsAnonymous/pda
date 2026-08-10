import { Button } from '@/components/ui/Button';
import { TextField } from '@/components/ui/TextField';

interface Props {
  options: readonly string[];
  onChange: (options: string[]) => void;
  hint?: string | undefined;
  maxLength?: number;
}

export function QuestionOptionsEditor({ options, onChange, hint, maxLength }: Props) {
  const rows = options.length === 0 ? [''] : [...options];

  function setRow(index: number, value: string) {
    const next = [...rows];
    next[index] = value;
    onChange(next);
  }

  function addRow() {
    onChange([...rows, '']);
  }

  function removeRow(index: number) {
    onChange(rows.filter((_, i) => i !== index));
  }

  return (
    <fieldset className="flex flex-col gap-2">
      <legend className="text-foreground text-sm font-medium">options</legend>
      {hint ? <p className="text-foreground-tertiary text-xs">{hint}</p> : null}
      <ul className="flex flex-col gap-2">
        {rows.map((option, index) => {
          const label = `option ${String(index + 1)}`;
          return (
            <li key={index} className="flex items-start gap-2">
              <div className="min-w-0 flex-1">
                <TextField
                  label={label}
                  hideLabel
                  value={option}
                  maxLength={maxLength}
                  onChange={(e) => {
                    setRow(index, e.target.value);
                  }}
                />
              </div>
              <Button
                type="button"
                variant="ghost"
                aria-label={`remove ${label}`}
                onClick={() => {
                  removeRow(index);
                }}
              >
                remove
              </Button>
            </li>
          );
        })}
      </ul>
      <Button type="button" variant="secondary" onClick={addRow} className="self-start">
        + add option
      </Button>
    </fieldset>
  );
}
