import { type Event, type RsvpInputStatus, RsvpStatus } from '@/models/event';
import { eventRequiresPaymentConfirmation } from '@/utils/eventCost';

export function usePaymentGate(event: Event) {
  return (status: RsvpInputStatus) =>
    eventRequiresPaymentConfirmation(event) &&
    status === RsvpStatus.Attending &&
    !event.myPaidConfirmed;
}
