import { TextField } from '@/components/ui/TextField';

import { RATING_SCALE_SIZE, scaleEndLabels } from './questionTypeOptions';

interface Props {
  id: string;
  options: string[];
  disabled: boolean;
  onChange: (options: string[]) => void;
  onCommit: (options: string[]) => void;
}

export function ScaleLabelFields({ id, options, disabled, onChange, onCommit }: Props) {
  const ends = scaleEndLabels(options);
  const fields = [
    { label: 'label for 1', placeholder: 'e.g. bad' },
    { label: `label for ${String(RATING_SCALE_SIZE)}`, placeholder: 'e.g. great' },
  ];

  return (
    <div className="flex flex-col gap-2">
      <p className="text-muted text-xs">optional — words under each end of the scale</p>
      <div className="grid grid-cols-2 gap-2">
        {fields.map(({ label, placeholder }, index) => (
          <TextField
            key={label}
            id={`${id}-scale-end-${String(index)}`}
            label={label}
            placeholder={placeholder}
            value={ends[index]}
            disabled={disabled}
            maxLength={200}
            onChange={(e) => {
              onChange(ends.map((end, i) => (i === index ? e.target.value : end)));
            }}
            onBlur={() => {
              onCommit(ends);
            }}
          />
        ))}
      </div>
    </div>
  );
}
