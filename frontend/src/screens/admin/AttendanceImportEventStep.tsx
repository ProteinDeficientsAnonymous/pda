import { format } from 'date-fns';
import { useState } from 'react';

import { type EventOption, useAttendanceImportEventOptions } from '@/api/attendanceImport';
import { Button } from '@/components/ui/Button';
import { TextField } from '@/components/ui/TextField';
import { Toggle } from '@/components/ui/Toggle';
import { EventType } from '@/models/event';

export interface EventTarget {
  eventId?: string;
  eventTitle?: string;
  eventDate?: string;
  eventType?: (typeof EventType)[keyof typeof EventType];
}

interface Props {
  onNext: (target: EventTarget) => void;
}

export function AttendanceImportEventStep({ onNext }: Props) {
  const [mode, setMode] = useState<'existing' | 'new'>('existing');
  const [query, setQuery] = useState('');
  const [newTitle, setNewTitle] = useState('');
  const [newDate, setNewDate] = useState('');
  const [newEventType, setNewEventType] = useState<(typeof EventType)[keyof typeof EventType]>(
    EventType.Community,
  );
  const { data: options = [] } = useAttendanceImportEventOptions(query);

  return (
    <div className="flex flex-col gap-4">
      <div
        role="tablist"
        aria-label="event source"
        className="border-border-strong bg-surface flex w-full rounded-full border p-1"
      >
        <ModeButton
          active={mode === 'existing'}
          onClick={() => {
            setMode('existing');
          }}
        >
          existing event
        </ModeButton>
        <ModeButton
          active={mode === 'new'}
          onClick={() => {
            setMode('new');
          }}
        >
          new event
        </ModeButton>
      </div>

      {mode === 'existing' ? (
        <ExistingEventPicker
          query={query}
          onQueryChange={setQuery}
          options={options}
          onPick={(id) => {
            onNext({ eventId: id });
          }}
        />
      ) : (
        <NewEventFields
          title={newTitle}
          date={newDate}
          eventType={newEventType}
          onTitleChange={setNewTitle}
          onDateChange={setNewDate}
          onEventTypeChange={setNewEventType}
          onNext={() => {
            onNext({ eventTitle: newTitle, eventDate: newDate, eventType: newEventType });
          }}
        />
      )}
    </div>
  );
}

function ModeButton({
  active,
  onClick,
  children,
}: {
  active: boolean;
  onClick: () => void;
  children: string;
}) {
  return (
    <button
      type="button"
      role="tab"
      aria-selected={active}
      onClick={onClick}
      className={`flex-1 rounded-full px-3 py-1 text-sm transition-colors ${
        active ? 'bg-brand-600 text-brand-on' : 'text-foreground-secondary hover:bg-surface-dim'
      }`}
    >
      {children}
    </button>
  );
}

function ExistingEventPicker({
  query,
  onQueryChange,
  options,
  onPick,
}: {
  query: string;
  onQueryChange: (v: string) => void;
  options: EventOption[];
  onPick: (eventId: string) => void;
}) {
  return (
    <div className="flex flex-col gap-2">
      <TextField
        label="search events"
        value={query}
        onChange={(e) => {
          onQueryChange(e.target.value);
        }}
        placeholder="search by title"
      />
      {options.length === 0 ? (
        <p className="text-muted text-sm">no events found</p>
      ) : (
        <ul className="border-border bg-surface max-h-64 overflow-y-auto rounded-md border">
          {options.map((o) => (
            <li key={o.id}>
              <button
                type="button"
                onClick={() => {
                  onPick(o.id);
                }}
                className="hover:bg-background flex w-full items-center justify-between px-3 py-2 text-start text-sm"
              >
                <span>{o.title.toLowerCase()}</span>
                <span className="text-muted text-xs">
                  {o.startDatetime ? format(o.startDatetime, 'MMM d, yyyy').toLowerCase() : ''}
                </span>
              </button>
            </li>
          ))}
        </ul>
      )}
    </div>
  );
}

function NewEventFields({
  title,
  date,
  eventType,
  onTitleChange,
  onDateChange,
  onEventTypeChange,
  onNext,
}: {
  title: string;
  date: string;
  eventType: (typeof EventType)[keyof typeof EventType];
  onTitleChange: (v: string) => void;
  onDateChange: (v: string) => void;
  onEventTypeChange: (v: (typeof EventType)[keyof typeof EventType]) => void;
  onNext: () => void;
}) {
  return (
    <div className="flex flex-col gap-3">
      <TextField
        label="event name"
        value={title}
        onChange={(e) => {
          onTitleChange(e.target.value);
        }}
        placeholder="e.g. summer potluck"
      />
      <TextField
        label="event date"
        type="date"
        value={date}
        onChange={(e) => {
          onDateChange(e.target.value);
        }}
      />
      <div className="flex flex-col gap-1">
        <Toggle
          label="official pda event"
          checked={eventType === EventType.Official}
          onChange={(checked) => {
            onEventTypeChange(checked ? EventType.Official : EventType.Community);
          }}
        />
        <Toggle
          label="pda club event"
          checked={eventType === EventType.Club}
          onChange={(checked) => {
            onEventTypeChange(checked ? EventType.Club : EventType.Community);
          }}
        />
      </div>
      <Button disabled={!title.trim() || !date} onClick={onNext}>
        continue
      </Button>
    </div>
  );
}
