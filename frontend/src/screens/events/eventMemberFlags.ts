import type { Event } from '@/models/event';
import { EventStatus, InvitePermission, RsvpStatus } from '@/models/event';
import { hasPermission, Permission } from '@/models/permissions';
import type { User } from '@/models/user';

export function eventMemberSectionFlags(event: Event, user: User | null) {
  const isCoHost =
    user !== null && (user.id === event.createdById || event.coHostIds.includes(user.id));
  const canManageEvents = user !== null && hasPermission(user, Permission.ManageEvents);
  const canSeeInvited = isCoHost || canManageEvents;
  const isCancelled = event.status === EventStatus.Cancelled;
  const rsvpDisabled = !event.rsvpEnabled;
  const hasRsvpd = event.myRsvp === RsvpStatus.Attending || event.myRsvp === RsvpStatus.Maybe;
  const canInvite =
    user !== null &&
    !isCancelled &&
    !event.isPast &&
    !rsvpDisabled &&
    (isCoHost ||
      canManageEvents ||
      (event.invitePermission === InvitePermission.AllMembers && hasRsvpd));
  const showRsvp = !event.isPast && event.rsvpEnabled && event.status !== EventStatus.Cancelled;
  const showStandaloneInvited = !showRsvp && canSeeInvited && event.invitedCount > 0;
  return { isCoHost, canSeeInvited, isCancelled, rsvpDisabled, canInvite, showRsvp, showStandaloneInvited };
}
