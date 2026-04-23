// Client-side event form validation. Mirrors what _events.py enforces, but
// lets the UI show field-level errors before the round-trip. The server is
// still the source of truth; we surface the returned `detail` on a 400.

import type { EventFormValues } from '@/api/eventWrites';

type Errors = Partial<Record<keyof EventFormValues, string>>;

export function validateEventForm(values: EventFormValues): Errors {
  const errors: Errors = {};
  if (!values.title.trim()) errors.title = 'required';
  else if (values.title.length > 200) errors.title = 'under 200 chars';

  if (values.description.length > 2000) errors.description = 'too long';
  if (values.location.length > 300) errors.location = 'under 300 chars';

  // Drafts can save without a start date (progress-capture). Active events
  // must have one. Either way, if a start is present it must be in the future.
  if (!values.datetimeTbd) {
    if (!values.startDatetime) {
      if (values.status !== 'draft') errors.startDatetime = 'required';
    } else if (new Date(values.startDatetime).getTime() < Date.now() - 60_000) {
      errors.startDatetime = 'start must be in the future';
    }
  }
  if (values.endDatetime && values.startDatetime) {
    if (new Date(values.endDatetime) <= new Date(values.startDatetime)) {
      errors.endDatetime = 'end must be after start';
    }
  }

  // null = unlimited (leave the field blank). Otherwise must be a positive
  // integer — 0 would let someone create an event nobody can rsvp to.
  if (
    values.maxAttendees !== null &&
    (values.maxAttendees < 1 || !Number.isFinite(values.maxAttendees))
  ) {
    errors.maxAttendees = 'must be 1 or more (leave blank for unlimited)';
  }
  return errors;
}
