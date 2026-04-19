// Always-visible zone: title, start + end, tbd toggle, location.
// Description / visibility / event type moved into the details section.
//
// Poll integration: a "propose dates" button lives above the start/end
// pickers. Two modes:
//   - create-flow (no existing event): opens PollCreateDialog in buffer
//     mode; the parent queues Date[]s and fires them after useCreateEvent.
//     Queued options hide the tbd toggle + pickers.
//   - edit-flow (existing, no poll): opens PollCreateDialog in live mode,
//     which POSTs immediately. Once the poll exists the parent re-renders
//     with timeLocked=true and the create button disappears.

import { useState } from 'react';
import { format } from 'date-fns';
import type { EventFormValues } from '@/api/eventWrites';
import { Button } from '@/components/ui/Button';
import { DateTimePicker } from '@/components/ui/DateTimePicker';
import { LocationField } from '@/components/ui/LocationField';
import { TextField } from '@/components/ui/TextField';
import { Toggle } from '@/components/ui/Toggle';
import { PollCreateDialog } from '@/screens/events/poll/PollCreateDialog';

interface Props {
  values: EventFormValues;
  onChange: (patch: Partial<EventFormValues>) => void;
  errors: Partial<Record<keyof EventFormValues, string>>;
  timeLocked?: boolean;
  existingEventId?: string;
  existingHasPoll?: boolean;
  bufferedPollOptions?: Date[] | null;
  onBufferPoll?: (dates: Date[] | null) => void;
}

export function EventFormBasics({
  values,
  onChange,
  errors,
  timeLocked = false,
  existingEventId,
  existingHasPoll = false,
  bufferedPollOptions,
  onBufferPoll,
}: Props) {
  const [pollOpen, setPollOpen] = useState(false);

  const isCreateFlow = !existingEventId;
  const bufferedDates = bufferedPollOptions && bufferedPollOptions.length > 0 ? bufferedPollOptions : null;
  // Show the "propose dates" button when:
  //   - edit flow, no poll yet (live mode), OR
  //   - create flow, nothing buffered yet (buffer mode).
  const canShowProposeButton =
    !timeLocked && (isCreateFlow ? !bufferedDates : !existingHasPoll);

  return (
    <div className="flex flex-col gap-4 rounded-[var(--radius-md)] border border-brand-100 bg-surface p-4 shadow-(--shadow-sm)">
      <TextField
        label="title"
        value={values.title}
        onChange={(e) => {
          onChange({ title: e.target.value });
        }}
        maxLength={200}
        placeholder="sunday potluck"
        error={errors.title}
        required
      />

      {timeLocked ? (
        <p className="text-sm text-neutral-600">
          date locked — a poll is active. finalize it to set the time.
        </p>
      ) : bufferedDates ? (
        <BufferedPollSummary
          dates={bufferedDates}
          onEdit={() => {
            setPollOpen(true);
          }}
          onClear={() => {
            onBufferPoll?.(null);
          }}
        />
      ) : (
        <>
          {canShowProposeButton ? (
            <Button
              variant="secondary"
              onClick={() => {
                setPollOpen(true);
              }}
              className="self-start"
            >
              propose dates (let members vote)
            </Button>
          ) : null}

          <Toggle
            label="date & time tbd"
            checked={values.datetimeTbd}
            onChange={(checked) => {
              onChange({ datetimeTbd: checked });
            }}
          />

          {!values.datetimeTbd ? (
            <div className="grid grid-cols-1 gap-4 sm:grid-cols-2">
              <DateTimePicker
                label="starts"
                value={values.startDatetime}
                onChange={(iso) => {
                  onChange({ startDatetime: iso });
                }}
                error={errors.startDatetime}
              />
              <DateTimePicker
                label="ends"
                value={values.endDatetime}
                onChange={(iso) => {
                  onChange({ endDatetime: iso });
                }}
                error={errors.endDatetime}
                optional
              />
            </div>
          ) : null}
        </>
      )}

      <PollCreateDialog
        open={pollOpen}
        onClose={() => {
          setPollOpen(false);
        }}
        eventId={isCreateFlow ? undefined : existingEventId}
        onBuffer={
          isCreateFlow && onBufferPoll
            ? (dates) => {
                onBufferPoll(dates);
                // Force tbd on so the backend accepts the event without a time.
                onChange({ datetimeTbd: true, startDatetime: null, endDatetime: null });
              }
            : undefined
        }
        initialOptions={
          isCreateFlow && bufferedDates ? bufferedDates.map((d) => d.toISOString()) : undefined
        }
      />

      <LocationField
        label="location"
        value={values.location}
        latitude={values.latitude}
        longitude={values.longitude}
        onChange={(patch) => {
          onChange(patch);
        }}
        maxLength={300}
        placeholder="address, neighborhood, or 'dm for details'"
        error={errors.location}
      />
    </div>
  );
}

function BufferedPollSummary({
  dates,
  onEdit,
  onClear,
}: {
  dates: readonly Date[];
  onEdit: () => void;
  onClear: () => void;
}) {
  const sorted = [...dates].sort((a, b) => a.getTime() - b.getTime());
  return (
    <div className="flex flex-col gap-2 rounded-md border border-dashed border-brand-300 bg-brand-50 p-3">
      <p className="text-sm font-medium text-brand-900">
        {dates.length} dates queued — vote opens after you save
      </p>
      <ul className="flex flex-col gap-0.5 text-xs text-foreground-secondary">
        {sorted.map((d) => (
          <li key={d.toISOString()}>{format(d, 'EEE MMM d · h:mm a').toLowerCase()}</li>
        ))}
      </ul>
      <div className="flex gap-2 pt-1">
        <Button variant="ghost" onClick={onEdit}>
          edit
        </Button>
        <Button variant="ghost" onClick={onClear}>
          clear
        </Button>
      </div>
    </div>
  );
}