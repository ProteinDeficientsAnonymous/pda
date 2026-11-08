import { useState } from 'react';
import { toast } from 'sonner';

import { extractApiErrorOr } from '@/api/apiErrors';
import {
  fetchAttendancePausePreview,
  type PauseImpactEvent,
  type PauseOutcome,
  type PauseRole,
} from '@/api/attendancePausePreview';
import { Toggle } from '@/components/ui/Toggle';
import { useConfirm } from '@/components/ui/useConfirm';
import { formatShortDateTime } from '@/utils/datetime';

const ROLE_LABEL: Record<PauseRole, string> = { rsvp: "rsvp'd", hosting: 'hosting' };
const OUTCOME_LABEL: Record<PauseOutcome, string> = {
  kept: 'kept',
  removed: 'removed',
  drafted: 'moved to draft',
};

export interface PauseState {
  isPaused: boolean;
  attendancePaused: boolean;
}

interface Props {
  memberId: string;
  value: PauseState;
  onChange: (next: PauseState) => void;
  targetIsAdmin: boolean;
}

export function MemberPauseToggles({ memberId, value, onChange, targetIsAdmin }: Props) {
  const [loading, setLoading] = useState(false);
  const [wasAttendancePaused] = useState(value.attendancePaused);
  const { confirm, element: confirmElement } = useConfirm();

  function setAttendancePaused(attendancePaused: boolean) {
    onChange({ ...value, attendancePaused });
  }

  async function onAttendanceToggle(next: boolean) {
    if (!next || wasAttendancePaused) {
      setAttendancePaused(next);
      return;
    }
    setLoading(true);
    try {
      const events = await fetchAttendancePausePreview(memberId);
      const ok =
        events.length === 0 ||
        (await confirm({
          title: 'pause for event rqmt?',
          message: `here's what happens to their upcoming events once you save:\n\n${events.map(describeImpact).join('\n')}`,
          confirmLabel: 'pause',
          destructive: true,
        }));
      if (ok) setAttendancePaused(true);
    } catch (err) {
      toast.error(extractApiErrorOr(err, "couldn't load their upcoming events — try again"));
    } finally {
      setLoading(false);
    }
  }

  return (
    <>
      <Toggle
        label="guidelines violation pause"
        checked={value.isPaused}
        onChange={(isPaused) => {
          onChange({ ...value, isPaused });
        }}
        disabled={targetIsAdmin || loading}
      />
      <Toggle
        label="event rqmt pause"
        checked={value.attendancePaused}
        onChange={(next) => void onAttendanceToggle(next)}
        disabled={targetIsAdmin || loading}
      />
      {targetIsAdmin ? <p className="text-muted text-xs">admins can't be paused</p> : null}
      {confirmElement}
    </>
  );
}

function describeImpact(e: PauseImpactEvent): string {
  const when = e.startDatetime ? formatShortDateTime(e.startDatetime) : 'date tbd';
  return `• ${e.title.toLowerCase()} (${when}) — ${ROLE_LABEL[e.role]} · ${OUTCOME_LABEL[e.outcome]}`;
}
