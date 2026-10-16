import { startOfToday } from 'date-fns';
import { useState } from 'react';

// Captured once at mount so render stays pure (React Compiler `purity` rule).
export function useToday(): Date {
  const [today] = useState(startOfToday);
  return today;
}
