import { TextField } from '@/components/ui/TextField';

import { ratingLabelSlots } from './questionTypeOptions';

interface Props {
  id: string;
  options: string[];
  disabled: boolean;
  onChange: (options: string[]) => void;
  onCommit: (options: string[]) => void;
}

export function RatingLabelFields({ id, options, disabled, onChange, onCommit }: Props) {
  const slots = ratingLabelSlots(options);

  function setSlot(index: number, value: string) {
    const next = [...slots];
    next[index] = value;
    return next;
  }

  return (
    <div className="flex flex-col gap-2">
      <p className="text-muted text-xs">optional labels — leave any star blank</p>
      <ul className="flex flex-col gap-2">
        {slots.map((slot, index) => {
          const label = `star ${String(index + 1)} label`;
          return (
            <li key={index} className="flex items-center gap-2">
              <span aria-hidden="true" className="text-muted w-4 text-end text-sm">
                {String(index + 1)}.
              </span>
              <div className="min-w-0 flex-1">
                <TextField
                  id={`${id}-star-${String(index)}`}
                  label={label}
                  hideLabel
                  placeholder={label}
                  value={slot}
                  disabled={disabled}
                  maxLength={200}
                  onChange={(e) => {
                    onChange(setSlot(index, e.target.value));
                  }}
                  onBlur={() => {
                    onCommit(slots);
                  }}
                />
              </div>
            </li>
          );
        })}
      </ul>
    </div>
  );
}
