import type { components } from './types.gen';

export type WireAttendedEvent = components['schemas']['AttendedEventOut'];

export interface AttendedEvent {
  eventId: string;
  title: string;
  startDatetime: Date | null;
  eventType: string;
}

export function mapAttendedEvent(w: WireAttendedEvent): AttendedEvent {
  return {
    eventId: w.event_id,
    title: w.title,
    startDatetime: w.start_datetime ? new Date(w.start_datetime) : null,
    eventType: w.event_type,
  };
}
