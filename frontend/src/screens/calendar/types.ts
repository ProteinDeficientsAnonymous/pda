import type { Event as PdaEvent } from '@/models/event';

export interface BigCalEvent {
  id: string;
  title: string;
  start: Date;
  end: Date;
  resource: PdaEvent;
}
