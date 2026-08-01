import type { Event } from '@/models/event';
import { EventStatus, InvitePermission, RsvpStatus } from '@/models/event';
import { hasPermission, Permission } from '@/models/permissions';
import type { User } from '@/models/user';

export function eventMemberSectionFlags(event: Event, user: User | null) {
  // co_hosts is the sole source of truth — created_by is a permanent audit
  // field and stays set after the creator steps down.
  const isCoHost = user !== null && event.coHostIds.includes(user.id);
  const canManageEvents = user !== null && hasPermission(user, Permission.ManageEvents);
  const isHostOrEventManager = isCoHost || canManageEvents;
  const isCancelled = event.status === EventStatus.Cancelled;
  const isOpen = !isCancelled && !event.isPast;
  const canEdit = isHostOrEventManager && isOpen;
  const hasRsvpd = event.myRsvp === RsvpStatus.Attending || event.myRsvp === RsvpStatus.Maybe;
  const canInvite =
    user !== null &&
    isOpen &&
    event.rsvpEnabled &&
    (isHostOrEventManager || (event.invitePermission === InvitePermission.AllMembers && hasRsvpd));
  const showRsvp = event.rsvpEnabled && !isCancelled;
  const rsvpLocked = event.isPast;
  const showStandaloneInvited = !showRsvp && isHostOrEventManager && event.invitedCount > 0;
  return {
    isHostOrEventManager,
    canEdit,
    canInvite,
    showRsvp,
    rsvpLocked,
    showStandaloneInvited,
  };
}
