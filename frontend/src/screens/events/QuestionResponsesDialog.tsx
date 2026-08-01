import { Dialog } from '@/components/ui/Dialog';
import type { Event } from '@/models/event';

import { EventRsvpResponsesSection } from './EventRsvpResponsesSection';

interface Props {
  event: Event;
  open: boolean;
  onClose: () => void;
}

export function QuestionResponsesDialog({ event, open, onClose }: Props) {
  if (!open || event.rsvpQuestions.length === 0) return null;

  return (
    <Dialog open={open} onClose={onClose} title="question responses" wide>
      <EventRsvpResponsesSection event={event} embedded />
    </Dialog>
  );
}
