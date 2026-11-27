import { startOfToday } from 'date-fns';
import { useState } from 'react';

import { startOfEventDay } from '@/utils/datetime';

// Captured once at mount so render stays pure (React Compiler `purity` rule).
export function useToday(): Date {
  const [today] = useState(startOfToday);
  return today;
}

export function useEventToday(): Date {
  const [today] = useState(() => startOfEventDay(new Date()));
  return today;
}
