import { useMemo, useState } from 'react';
import { Calendar, type View } from 'react-big-calendar';
import 'react-big-calendar/lib/css/react-big-calendar.css';
import { useNavigate } from 'react-router-dom';
import { useEvents } from '@/api/events';
import { useAuthStore } from '@/auth/store';
import type { Event as PdaEvent } from '@/models/event';
import { eventClass } from '@/models/event';
import { makeLocalizer } from './calendarLocalizer';
import { ViewSwitcher } from './ViewSwitcher';

interface BigCalEvent {
  id: string;
  title: string;
  start: Date;
  end: Date;
  resource: PdaEvent;
}

function toBigCalEvent(e: PdaEvent): BigCalEvent {
  // big-calendar requires both start + end. Fall back to +1h for events that
  // only have a start time (which is fine for rendering purposes).
  const end = e.endDatetime ?? new Date(e.startDatetime.getTime() + 60 * 60 * 1000);
  return { id: e.id, title: e.title, start: e.startDatetime, end, resource: e };
}

export default function CalendarScreen() {
  const navigate = useNavigate();
  const user = useAuthStore((s) => s.user);
  const weekStartsOn: 0 | 1 = user?.weekStart === 'monday' ? 1 : 0;
  const localizer = useMemo(() => makeLocalizer(weekStartsOn), [weekStartsOn]);

  const { data: events = [], isPending, isError, refetch } = useEvents();
  const bigCalEvents = useMemo<BigCalEvent[]>(
    () => events.filter((e) => !e.datetimeTbd).map(toBigCalEvent),
    [events],
  );

  const [view, setView] = useState<View>('month');
  const [date, setDate] = useState<Date>(new Date());

  return (
    <main className="mx-auto max-w-6xl px-4 py-6">
      <header className="mb-4 flex flex-wrap items-center justify-between gap-3">
        <h1 className="text-2xl font-medium tracking-tight">calendar</h1>
        <ViewSwitcher value={view} onChange={setView} />
      </header>

      {isError ? (
        <div className="mb-4 rounded-md border border-red-200 bg-red-50 px-3 py-2 text-sm text-red-700">
          couldn't load events —{' '}
          <button
            type="button"
            onClick={() => {
              void refetch();
            }}
            className="underline"
          >
            try again
          </button>
        </div>
      ) : null}

      <div className="rounded-lg border border-neutral-200 bg-white p-2">
        <Calendar<BigCalEvent>
          localizer={localizer}
          events={bigCalEvents}
          startAccessor="start"
          endAccessor="end"
          view={view}
          onView={setView}
          date={date}
          onNavigate={setDate}
          views={['month', 'week', 'day', 'agenda']}
          popup
          eventPropGetter={(evt) => ({
            className: eventClass(evt.resource),
          })}
          onSelectEvent={(evt) => {
            void navigate(`/events/${evt.id}`);
          }}
          onDrillDown={(d) => {
            setDate(d);
            setView('day');
          }}
          style={{ height: '72vh' }}
        />
        {isPending ? (
          <p className="mt-2 text-center text-xs text-neutral-500">loading events…</p>
        ) : null}
      </div>
    </main>
  );
}
