import { format, getDay, parse, startOfWeek } from 'date-fns';
import { enUS } from 'date-fns/locale';
import { dateFnsLocalizer } from 'react-big-calendar';

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
