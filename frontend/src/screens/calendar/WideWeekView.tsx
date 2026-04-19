// Wide-screen week view — 7 day columns, no time grid. Mirrors the narrow
// week view's clean chip layout but horizontal. Events within each day are
// stacked in chronological order; if there isn't enough vertical room for
// all of them, the last visible slot becomes a "+N more" indicator that
// drills into that day.

import { addDays, format, isSameDay, startOfWeek } from 'date-fns';
import { useLayoutEffect, useRef, useState } from 'react';
import { eventClass, type Event as PdaEvent } from '@/models/event';
import { cn } from '@/utils/cn';

interface Props {
  date: Date;
  weekStartsOn: 0 | 1;
  events: PdaEvent[];
  onSelectEvent: (event: PdaEvent) => void;
  onSelectDay: (day: Date) => void;
}

const lower = (d: Date, f: string) => format(d, f).toLowerCase();

export function WideWeekView({ date, weekStartsOn, events, onSelectEvent, onSelectDay }: Props) {
  const weekStart = startOfWeek(date, { weekStartsOn });
  const days = Array.from({ length: 7 }, (_, i) => addDays(weekStart, i));
  const today = new Date();

  return (
    <div
      aria-label="week"
      role="grid"
      className="grid h-full grid-cols-7 overflow-hidden rounded-md border border-border/80 bg-surface"
    >
      {days.map((day, idx) => (
        <DayColumn
          key={day.toISOString()}
          day={day}
          isLast={idx === 6}
          isToday={isSameDay(day, today)}
          events={eventsForDay(events, day)}
          onSelectEvent={onSelectEvent}
          onSelectDay={onSelectDay}
        />
      ))}
    </div>
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

interface DayColumnProps {
  day: Date;
  isLast: boolean;
  isToday: boolean;
  events: PdaEvent[];
  onSelectEvent: (event: PdaEvent) => void;
  onSelectDay: (day: Date) => void;
}

function DayColumn({ day, isLast, isToday, events, onSelectEvent, onSelectDay }: DayColumnProps) {
  const weekdayLabel = lower(day, 'EEE');
  const dayNumber = format(day, 'd');

  return (
    <div
      role="gridcell"
      aria-label={`${weekdayLabel} ${dayNumber}`}
      className={cn('flex min-h-0 flex-col', !isLast && 'border-r border-border/60')}
    >
      <div className="flex items-center justify-center border-b border-border/60 px-1 py-2">
        <div
          className={cn(
            'flex items-center gap-1.5 rounded-md px-1.5 py-1 leading-tight',
            isToday ? 'bg-brand-600 text-brand-on' : 'text-foreground-secondary',
          )}
        >
          <span className={cn('text-xs', isToday ? 'text-brand-on' : 'text-muted')}>
            {weekdayLabel}
          </span>
          <span className="text-base font-medium">{dayNumber}</span>
        </div>
      </div>
      <DayEvents
        events={events}
        onSelectEvent={onSelectEvent}
        onOverflow={() => {
          onSelectDay(day);
        }}
      />
    </div>
  );
}

interface DayEventsProps {
  events: PdaEvent[];
  onSelectEvent: (event: PdaEvent) => void;
  onOverflow: () => void;
}

// Rough per-chip height (px) — used for the first paint before we measure.
// Matches the chip's padding + single-line text so the initial budget is
// close and the post-measurement recalc is usually a no-op.
const ESTIMATED_CHIP_HEIGHT = 28;

function DayEvents({ events, onSelectEvent, onOverflow }: DayEventsProps) {
  const containerRef = useRef<HTMLDivElement | null>(null);
  const [capacity, setCapacity] = useState<number>(() =>
    Math.max(1, Math.floor(200 / ESTIMATED_CHIP_HEIGHT)),
  );

  useLayoutEffect(() => {
    const el = containerRef.current;
    if (!el) return;
    const measure = () => {
      const available = el.clientHeight;
      const chipH = ESTIMATED_CHIP_HEIGHT;
      setCapacity(Math.max(1, Math.floor(available / chipH)));
    };
    measure();
    const obs = new ResizeObserver(measure);
    obs.observe(el);
    return () => {
      obs.disconnect();
    };
  }, []);

  // Reserve one slot for the "+N more" row when we can't fit everything.
  const showOverflow = events.length > capacity;
  const visibleCount = showOverflow ? Math.max(0, capacity - 1) : events.length;
  const visible = events.slice(0, visibleCount);
  const overflow = events.length - visibleCount;

  return (
    <div ref={containerRef} className="flex min-h-0 flex-1 flex-col gap-1 overflow-hidden p-1.5">
      {visible.map((event) => (
        <EventChip key={event.id} event={event} onSelect={onSelectEvent} />
      ))}
      {showOverflow ? (
        <button
          type="button"
          onClick={onOverflow}
          className="text-brand-700 hover:text-brand-800 text-left text-[11px] font-medium underline decoration-dotted"
        >
          {String(overflow)} more
        </button>
      ) : null}
    </div>
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
      className={cn(eventClass(event), 'flex w-full items-center gap-1.5 text-left')}
    >
      {time ? <span className="shrink-0 text-[11px] font-medium">{time}</span> : null}
      <span className="truncate text-[11px]">{event.title}</span>
    </button>
  );
}
