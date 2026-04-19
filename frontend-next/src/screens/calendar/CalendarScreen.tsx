import { addDays, format as dfFormat, startOfWeek } from 'date-fns';
import { useMemo, useState } from 'react';
import { Calendar, type View } from 'react-big-calendar';
import 'react-big-calendar/lib/css/react-big-calendar.css';
import { useNavigate } from 'react-router-dom';
import { useEvents } from '@/api/events';
import { useAuthStore } from '@/auth/store';
import { useIsWideScreen } from '@/hooks/useResponsive';
import { eventClass, type Event as PdaEvent } from '@/models/event';
import { CalendarToolbar } from './CalendarToolbar';
import { makeLocalizer } from './calendarLocalizer';
import { AgendaList } from './AgendaList';
import { DayEventList } from './DayEventList';
import { NarrowWeekView } from './NarrowWeekView';
import { TodayIconButton } from './TodayIconButton';
import type { BigCalEvent } from './types';
import { ViewSwitcher } from './ViewSwitcher';

function toBigCalEvent(e: PdaEvent): BigCalEvent | null {
  // TBD events have no date — skip them on the calendar.
  if (!e.startDatetime) return null;
  const end = e.endDatetime ?? new Date(e.startDatetime.getTime() + 60 * 60 * 1000);
  return { id: e.id, title: e.title, start: e.startDatetime, end, resource: e };
}

const lower = (d: Date, f: string) => dfFormat(d, f).toLowerCase();

const FORMATS = {
  weekdayFormat: (d: Date) => lower(d, 'EEE'),
  dayFormat: (d: Date) => lower(d, 'EEE d'),
  monthHeaderFormat: (d: Date) => lower(d, 'MMMM yyyy'),
  dayHeaderFormat: (d: Date) => lower(d, 'EEEE, MMM d'),
  dayRangeHeaderFormat: ({ start, end }: { start: Date; end: Date }) =>
    `${lower(start, 'MMM d')} – ${lower(end, 'MMM d')}`,
  agendaHeaderFormat: ({ start, end }: { start: Date; end: Date }) =>
    `${lower(start, 'MMM d')} – ${lower(end, 'MMM d')}`,
  agendaDateFormat: (d: Date) => lower(d, 'EEE MMM d'),
  agendaTimeFormat: (d: Date) => lower(d, 'h:mmaaa'),
  eventTimeRangeFormat: ({ start, end }: { start: Date; end: Date }) =>
    `${lower(start, 'h:mmaaa')} – ${lower(end, 'h:mmaaa')}`,
};

const MESSAGES = {
  noEventsInRange: 'nothing on this range — pop back later 🌿',
  showMore: (n: number) => `${String(n)} more`,
  today: 'today',
  previous: 'previous',
  next: 'next',
  month: 'month',
  week: 'week',
  day: 'day',
  agenda: 'list',
  date: 'date',
  time: 'time',
  event: 'event',
  allDay: 'all day',
};

export default function CalendarScreen() {
  const navigate = useNavigate();
  const user = useAuthStore((s) => s.user);
  const weekStartsOn: 0 | 1 = user?.weekStart === 'monday' ? 1 : 0;
  const localizer = useMemo(() => makeLocalizer(weekStartsOn), [weekStartsOn]);
  const isWide = useIsWideScreen(720);

  const { data: events = [], isPending, isError, refetch } = useEvents();
  const bigCalEvents = useMemo<BigCalEvent[]>(
    () =>
      events
        .filter((e) => !e.datetimeTbd)
        .map(toBigCalEvent)
        .filter((e): e is BigCalEvent => e !== null),
    [events],
  );
  const datedEvents = useMemo(() => events.filter((e) => !e.datetimeTbd), [events]);

  const [view, setView] = useState<View>('month');
  const [date, setDate] = useState<Date>(new Date());
  const useNarrowWeek = view === 'week' && !isWide;
  const useDayList = view === 'day';
  const useAgendaList = view === 'agenda';

  const goToEvent = (e: PdaEvent) => {
    void navigate(`/events/${e.id}`);
  };

  return (
    <main className="mx-auto max-w-6xl px-4 py-6">
      <header className="mb-4 flex justify-center">
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

      <div
        className="flex flex-col bg-white p-1"
        style={{ height: 'calc(100dvh - 14rem)' }}
      >
        {useNarrowWeek ? (
          <>
            <NarrowWeekToolbar date={date} weekStartsOn={weekStartsOn} onNavigate={setDate} />
            <div className="flex-1 overflow-y-auto">
              <NarrowWeekView
                date={date}
                weekStartsOn={weekStartsOn}
                events={datedEvents}
                onSelectEvent={goToEvent}
              />
            </div>
          </>
        ) : useDayList ? (
          <>
            <DayToolbar date={date} onNavigate={setDate} />
            <div className="flex-1 overflow-y-auto">
              <DayEventList date={date} events={datedEvents} onSelectEvent={goToEvent} />
            </div>
          </>
        ) : useAgendaList ? (
          <div className="flex-1 overflow-y-auto">
            <AgendaList events={datedEvents} onSelectEvent={goToEvent} />
          </div>
        ) : (
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
            formats={FORMATS}
            messages={MESSAGES}
            components={{ toolbar: CalendarToolbar }}
            eventPropGetter={(evt) => ({
              className: eventClass(evt.resource),
            })}
            onSelectEvent={(evt) => {
              goToEvent(evt.resource);
            }}
            onDrillDown={(d) => {
              setDate(d);
              setView('day');
            }}
            style={{ height: '100%' }}
          />
        )}
        {isPending ? (
          <p className="mt-2 text-center text-xs text-neutral-500">loading events…</p>
        ) : null}
      </div>
    </main>
  );
}

interface NarrowWeekToolbarProps {
  date: Date;
  weekStartsOn: 0 | 1;
  onNavigate: (date: Date) => void;
}

interface DayToolbarProps {
  date: Date;
  onNavigate: (date: Date) => void;
}

function DayToolbar({ date, onNavigate }: DayToolbarProps) {
  const label = lower(date, 'EEEE, MMM d');
  return (
    <div className="mb-2 flex items-center justify-between gap-2 px-1">
      <TodayIconButton
        onClick={() => {
          onNavigate(new Date());
        }}
      />
      <div className="flex items-center gap-1">
        <button
          type="button"
          aria-label="previous day"
          onClick={() => {
            onNavigate(addDays(date, -1));
          }}
          className="hover:text-brand-700 inline-flex h-8 w-8 items-center justify-center rounded-md text-neutral-600 hover:bg-neutral-100"
        >
          ‹
        </button>
        <span className="min-w-[10rem] text-center text-sm font-medium text-neutral-800">
          {label}
        </span>
        <button
          type="button"
          aria-label="next day"
          onClick={() => {
            onNavigate(addDays(date, 1));
          }}
          className="hover:text-brand-700 inline-flex h-8 w-8 items-center justify-center rounded-md text-neutral-600 hover:bg-neutral-100"
        >
          ›
        </button>
      </div>
      <span className="w-14" aria-hidden="true" />
    </div>
  );
}

function NarrowWeekToolbar({ date, weekStartsOn, onNavigate }: NarrowWeekToolbarProps) {
  const weekStart = startOfWeek(date, { weekStartsOn });
  const label = `week of ${lower(weekStart, 'MMM d')}`;
  return (
    <div className="mb-2 flex items-center justify-between gap-2 px-1">
      <TodayIconButton
        onClick={() => {
          onNavigate(new Date());
        }}
      />
      <div className="flex items-center gap-1">
        <button
          type="button"
          aria-label="previous week"
          onClick={() => {
            onNavigate(addDays(date, -7));
          }}
          className="hover:text-brand-700 inline-flex h-8 w-8 items-center justify-center rounded-md text-neutral-600 hover:bg-neutral-100"
        >
          ‹
        </button>
        <span className="min-w-[9rem] text-center text-sm font-medium text-neutral-800">
          {label}
        </span>
        <button
          type="button"
          aria-label="next week"
          onClick={() => {
            onNavigate(addDays(date, 7));
          }}
          className="hover:text-brand-700 inline-flex h-8 w-8 items-center justify-center rounded-md text-neutral-600 hover:bg-neutral-100"
        >
          ›
        </button>
      </div>
      <span className="w-14" aria-hidden="true" />
    </div>
  );
}
