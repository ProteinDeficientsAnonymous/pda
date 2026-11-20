import type { Event } from '@/models/event';
import { formatCents } from '@/utils/orderPrice';

import { savedOrderTotalCents } from './orderTotal';
import { isRsvpRespondentStatus } from './rsvpQuestions';

export function MyOrderTotal({ event }: { event: Event }) {
  if (!event.myRsvp || !isRsvpRespondentStatus(event.myRsvp)) return null;
  const total = savedOrderTotalCents(event.rsvpQuestions, event.myQuestionnaireResponses);
  if (total === null) return null;
  return <p className="text-foreground text-center text-sm">your order: {formatCents(total)}</p>;
}
