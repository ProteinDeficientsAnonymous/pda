import { useCallback, useMemo, useState } from 'react';

import { type ConsentTypeValue, missingConsents } from '@/models/consent';
import type { User } from '@/models/user';

// Shared state for the consent checkboxes: which consents are still outstanding
// for the user, which the user has ticked, whether all required boxes are ticked,
// and the list of types to submit. Drives both OnboardingScreen and ConsentScreen.
export function useConsentChecklist(user: User | null) {
  const consents = useMemo(() => missingConsents(user), [user]);
  const [checked, setChecked] = useState<ReadonlySet<ConsentTypeValue>>(new Set());

  const toggle = useCallback((type: ConsentTypeValue, isChecked: boolean) => {
    setChecked((prev) => {
      const next = new Set(prev);
      if (isChecked) next.add(type);
      else next.delete(type);
      return next;
    });
  }, []);

  // Every outstanding consent must be ticked before the form can submit.
  const allChecked = consents.every((c) => checked.has(c.type));
  const acceptedTypes = consents.filter((c) => checked.has(c.type)).map((c) => c.type);

  return { consents, checked, toggle, allChecked, acceptedTypes };
}
