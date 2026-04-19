// Mobile-first week view — days become rows instead of columns. Mirrors the
// Flutter `week_view_narrow.dart` layout: a fixed left column with the weekday
// + date (today gets a filled brand pill), and the day's events stack as
// colored chips on the right. Multi-day events only show on their start day.

import { addDays, format, isSameDay, startOfWeek } from 'date-fns';
import { eventClass, type Event as PdaEvent } from '@/models/event';
import { cn } from '@/utils/cn';

interface Props {
  date: Date;
  weekStartsOn: 0 | 1;
  events: PdaEvent[];
  onSelectEvent: (event: PdaEvent) => void;
}

const lower = (d: Date, f: string) => format(d, f).toLowerCase();

export function NarrowWeekView({ date, weekStartsOn, events, onSelectEvent }: Props) {
  const weekStart = startOfWeek(date, { weekStartsOn });
  const days = Array.from({ length: 7 }, (_, i) => addDays(weekStart, i));
  const today = new Date();

  return (
    <ul
      aria-label="week"
      className="overflow-hidden rounded-md border border-neutral-200/80 bg-white"
    >
      {days.map((day, idx) => (
        <DayRow
          key={day.toISOString()}
          day={day}
          isLast={idx === 6}
          isToday={isSameDay(day, today)}
          events={eventsForDay(events, day)}
          onSelectEvent={onSelectEvent}
        />
      ))}
    </ul>
  );
}

function eventsForDay(events: PdaEvent[], day: Date): PdaEvent[] {
  return events
    .filter((e) => e.startDatetime && isSameDay(e.startDatetime, day))
    .sort((a, b) => {
      const at = a.startDatetime?.getTime() ?? 0;
      const bt = b.startDatetime?.getTime() ?? 0;
      return at - bt;
    });
}

interface DayRowProps {
  day: Date;
  isLast: boolean;
  isToday: boolean;
  events: PdaEvent[];
  onSelectEvent: (event: PdaEvent) => void;
}

const MAX_CHIPS_PER_DAY = 2;

function DayRow({ day, isLast, isToday, events, onSelectEvent }: DayRowProps) {
  const weekdayLabel = lower(day, 'EEE');
  const dayNumber = format(day, 'd');
  const visibleEvents = events.slice(0, MAX_CHIPS_PER_DAY);
  const overflowCount = events.length - visibleEvents.length;
  return (
    <li
      aria-label={`${weekdayLabel} ${dayNumber}`}
      className={cn(
        'flex h-20 items-stretch',
        !isLast && 'border-b border-neutral-200/60',
      )}
    >
      <div className="flex w-14 shrink-0 items-center justify-center border-r border-neutral-200/60 px-1 py-2">
        <div
          className={cn(
            'flex flex-col items-center justify-center rounded-md px-1.5 py-1 text-center leading-tight',
            isToday ? 'bg-brand-600 text-white' : 'text-neutral-700',
          )}
        >
          <span className={cn('text-xs', isToday ? 'text-white' : 'text-neutral-500')}>
            {weekdayLabel}
          </span>
          <span className="text-base font-medium">{dayNumber}</span>
        </div>
      </div>

      <div className="flex min-w-0 flex-1 flex-col justify-center gap-1 overflow-hidden px-2 py-1.5">
        {visibleEvents.map((event) => (
          <EventChip key={event.id} event={event} onSelect={onSelectEvent} />
        ))}
        {overflowCount > 0 ? (
          <span className="text-brand-700 text-[11px] font-medium">
            {String(overflowCount)} more
          </span>
        ) : null}
      </div>
    </li>
  );
}

function EventChip({ event, onSelect }: { event: PdaEvent; onSelect: (event: PdaEvent) => void }) {
  const time = event.startDatetime ? lower(event.startDatetime, 'h:mmaaa') : '';
  return (
    <button
      type="button"
      onClick={() => {
        onSelect(event);
      }}
      className={cn(eventClass(event), 'flex w-full items-center gap-2 text-left')}
    >
      {time ? <span className="shrink-0 font-medium">{time}</span> : null}
      <span className="truncate">{event.title}</span>
    </button>
  );
}
