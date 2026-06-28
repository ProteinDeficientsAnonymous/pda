import { Link } from 'react-router-dom';
import type { ConsentDescriptor, ConsentTypeValue } from '@/models/consent';

interface ConsentChecklistProps {
  // The consents to render a checkbox for — typically missingConsents(user).
  consents: readonly ConsentDescriptor[];
  // Currently-checked consent types (controlled by the parent).
  checked: ReadonlySet<ConsentTypeValue>;
  onToggle: (type: ConsentTypeValue, checked: boolean) => void;
}

// Renders one checkbox per outstanding consent, driven by the consent registry.
// Used by both OnboardingScreen and ConsentScreen so the checkbox markup and
// copy live in exactly one place.
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
