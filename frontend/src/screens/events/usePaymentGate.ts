import { useFlag } from '@/api/featureFlags';
import { type Event, type RsvpInputStatus, RsvpStatus } from '@/models/event';
import { Feature } from '@/models/featureFlags';
import { eventRequiresPaymentConfirmation } from '@/utils/eventCost';

export function usePaymentGate(event: Event) {
  const flagOn = useFlag(Feature.EventPaymentConfirmation);
  return (status: RsvpInputStatus) =>
    eventRequiresPaymentConfirmation(event) &&
    flagOn &&
    status === RsvpStatus.Attending &&
    !event.myPaidConfirmed;
}
