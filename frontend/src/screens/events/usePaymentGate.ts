import { type Event, goingWouldWaitlist, type RsvpInputStatus, RsvpStatus } from '@/models/event';
import { eventRequiresPaymentConfirmation } from '@/utils/eventCost';

export function usePaymentGate(event: Event) {
  return (status: RsvpInputStatus, hasPlusOne: boolean) =>
    eventRequiresPaymentConfirmation(event) &&
    status === RsvpStatus.Attending &&
    !goingWouldWaitlist(event, hasPlusOne) &&
    !event.myPaidConfirmed;
}
