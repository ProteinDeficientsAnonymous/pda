// date-fns localizer for react-big-calendar. Respects the user's weekStart
// preference (Sunday=0 | Monday=1), defaulting to Sunday to match the project
// rule that weekStart is user-configurable on the profile.

import { dateFnsLocalizer } from 'react-big-calendar';
import { format, parse, startOfWeek, getDay } from 'date-fns';
import { enUS } from 'date-fns/locale';

export function makeLocalizer(weekStartsOn: 0 | 1) {
  const locales = { 'en-US': enUS };
  return dateFnsLocalizer({
    format,
    parse,
    startOfWeek: (date: Date) => startOfWeek(date, { weekStartsOn }),
    getDay,
    locales,
  });
}
