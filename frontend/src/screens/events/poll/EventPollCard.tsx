// Orchestrator for the datetime-poll block on an event detail page.
// Owns dialog open-states; decides which branch to render based on who the
// viewer is and what state the poll is in. Dialog bodies live in sibling
// files (Phase 3); this file stays focused on branching + layout.

import { useState } from 'react';
import { Link } from 'react-router-dom';
import { format } from 'date-fns';
import { useEventPoll } from '@/api/eventPolls';
import { useAuthStore } from '@/auth/store';
import { Button } from '@/components/ui/Button';
import type { Event } from '@/models/event';
import { hasPermission, Permission, type UserLike } from '@/models/permissions';
import { PollFinalizeDialog } from './PollFinalizeDialog';
import { PollManageDialog } from './PollManageDialog';
import { PollOptionStrip } from './PollOptionStrip';
import { PollRespondDialog } from './PollRespondDialog';

interface Props {
  event: Event;
}

export function EventPollCard({ event }: Props) {
  const user = useAuthStore((s) => s.user);
  const isAuthed = useAuthStore((s) => s.status === 'authed');
  const canManage = canManagePoll(event, user);

  const { data: poll, isPending, isError } = useEventPoll(event.id, event.hasPoll);

  const [respondOpen, setRespondOpen] = useState(false);
  const [finalizeOpen, setFinalizeOpen] = useState(false);
  const [manageOpen, setManageOpen] = useState(false);

  // No poll — the form owns poll creation; the detail screen just falls back
  // to the parent's "date & time tbd" line.
  if (!event.hasPoll) {
    return null;
  }

  if (isPending) {
    return <p className="text-foreground-tertiary text-sm">loading poll…</p>;
  }
  if (isError || !poll) {
    return (
      <p className="text-foreground-tertiary text-sm">couldn't load the poll — try refreshing</p>
    );
  }

  // Finalized — parent resumes the normal datetime line.
  if (poll.winningDatetime) {
    return null;
  }

  return (
    <div className="border-border bg-surface flex flex-col gap-3 rounded-md border p-4">
      <div className="flex items-center justify-between gap-2">
        <h2 className="text-sm font-medium">find a time</h2>
        <span className="text-foreground-tertiary text-xs">
          {poll.options.length} {poll.options.length === 1 ? 'option' : 'options'}
        </span>
      </div>

      <PollOptionStrip poll={poll} />

      <div className="flex flex-wrap gap-2">
        {isAuthed ? (
          <Button
            variant="secondary"
            onClick={() => {
              setRespondOpen(true);
            }}
          >
            respond to poll
          </Button>
        ) : (
          <Link
            to="/login"
            className="border-border-strong text-foreground-secondary hover:bg-background inline-flex h-10 items-center rounded-md border px-4 text-sm font-medium"
          >
            sign in to vote
          </Link>
        )}
        {canManage ? (
          <>
            <Button
              onClick={() => {
                setFinalizeOpen(true);
              }}
            >
              finalize
            </Button>
            <Button
              variant="ghost"
              onClick={() => {
                setManageOpen(true);
              }}
            >
              edit options
            </Button>
          </>
        ) : null}
      </div>

      {poll.finalizedAt ? (
        <p className="text-foreground-tertiary text-xs">
          finalized {format(poll.finalizedAt, 'MMM d').toLowerCase()}
        </p>
      ) : null}

      <PollRespondDialog
        open={respondOpen}
        onClose={() => {
          setRespondOpen(false);
        }}
        poll={poll}
      />
      <PollFinalizeDialog
        open={finalizeOpen}
        onClose={() => {
          setFinalizeOpen(false);
        }}
        event={event}
        poll={poll}
      />
      <PollManageDialog
        open={manageOpen}
        onClose={() => {
          setManageOpen(false);
        }}
        poll={poll}
      />
    </div>
  );
}

function canManagePoll(event: Event, user: (UserLike & { id: string }) | null): boolean {
  if (!user) return false;
  if (event.createdById === user.id) return true;
  if (event.coHostIds.includes(user.id)) return true;
  return hasPermission(user, Permission.ManageEvents);
}
