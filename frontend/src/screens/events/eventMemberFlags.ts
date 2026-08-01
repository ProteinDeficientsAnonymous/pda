import type { Event } from '@/models/event';
import { EventStatus, InvitePermission, RsvpStatus } from '@/models/event';
import { hasPermission, Permission } from '@/models/permissions';
import type { User } from '@/models/user';

export function eventMemberSectionFlags(event: Event, user: User | null) {
  // co_hosts is the sole source of truth — created_by is a permanent audit
  // field and stays set after the creator steps down.
  const isCoHost = user !== null && event.coHostIds.includes(user.id);
  const canManageEvents = user !== null && hasPermission(user, Permission.ManageEvents);
  const canSeeInvited = isCoHost || canManageEvents;
  const isCancelled = event.status === EventStatus.Cancelled;
  const isHostManager = (isCoHost || canManageEvents) && !isCancelled && !event.isPast;
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
  return {
    isCoHost,
    canSeeInvited,
    isHostManager,
    isCancelled,
    rsvpDisabled,
    canInvite,
    showRsvp,
    showStandaloneInvited,
  };
}
