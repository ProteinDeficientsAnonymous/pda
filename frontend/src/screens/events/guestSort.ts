import type { EventGuest, RsvpServerStatusValue } from '@/models/event';
import { RsvpServerStatus } from '@/models/event';

export function countWithPlusOnes(guests: EventGuest[]): number {
  return guests.reduce((acc, g) => acc + 1 + (g.hasPlusOne ? 1 : 0), 0);
}

const AVATAR_TIERS: { status: RsvpServerStatusValue; isMember: boolean }[] = [
  { status: RsvpServerStatus.Attending, isMember: true },
  { status: RsvpServerStatus.Maybe, isMember: true },
  { status: RsvpServerStatus.Attending, isMember: false },
  { status: RsvpServerStatus.Maybe, isMember: false },
];

export const PREVIEW_LIMIT = 5;

export function previewGuests(guests: EventGuest[], limit: number): EventGuest[] {
  return AVATAR_TIERS.flatMap((tier) =>
    guests.filter((g) => g.status === tier.status && g.isMember === tier.isMember),
  ).slice(0, limit);
}
