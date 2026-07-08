import { Link } from 'react-router-dom';
import type { ConsentDescriptor, ConsentTypeValue } from '@/models/consent';

interface ConsentChecklistProps {
  consents: readonly ConsentDescriptor[];
  checked: ReadonlySet<ConsentTypeValue>;
  onToggle: (type: ConsentTypeValue, checked: boolean) => void;
}

export function ConsentChecklist({ consents, checked, onToggle }: ConsentChecklistProps) {
  return (
    <>
      {consents.map((consent) => (
        <label
          key={consent.type}
          className="text-foreground flex items-start gap-2 text-sm leading-relaxed"
        >
          <input
            type="checkbox"
            checked={checked.has(consent.type)}
            onChange={(e) => {
              onToggle(consent.type, e.target.checked);
            }}
            className="mt-1"
          />
          <span>
            {consent.before}
            <Link to={consent.linkTo} target="_blank" className="text-brand-700 underline">
              {consent.linkLabel}
            </Link>
            {consent.after}
          </span>
        </label>
      ))}
    </>
  );
}
