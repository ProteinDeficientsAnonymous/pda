import { useState } from 'react';
import { toast } from 'sonner';

import { extractApiErrorOr } from '@/api/apiErrors';
import {
  fetchAttendancePausePreview,
  fetchGuidelinesPausePreview,
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

const PAUSE_DIALOG = {
  guidelinesPaused: {
    fetchPreview: fetchGuidelinesPausePreview,
    title: 'pause for guidelines violation?',
  },
  attendancePaused: { fetchPreview: fetchAttendancePausePreview, title: 'pause for event rqmt?' },
};

export interface PauseState {
  guidelinesPaused: boolean;
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
  const [initial] = useState(value);
  const { confirm, element: confirmElement } = useConfirm();

  async function onToggle(field: keyof PauseState, next: boolean) {
    // A guidelines pause replaces an event rqmt pause, so drop any pending event rqmt change.
    const base =
      field === 'guidelinesPaused'
        ? { ...value, attendancePaused: initial.attendancePaused }
        : value;
    if (!next || initial[field]) {
      onChange({ ...base, [field]: next });
      return;
    }
    const { fetchPreview, title } = PAUSE_DIALOG[field];
    setLoading(true);
    try {
      const events = await fetchPreview(memberId);
      const ok =
        events.length === 0 ||
        (await confirm({
          title,
          message: `here's what happens to their upcoming events once you save:\n\n${events.map(describeImpact).join('\n')}`,
          confirmLabel: 'pause',
          destructive: true,
        }));
      if (ok) onChange({ ...base, [field]: true });
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
        checked={value.guidelinesPaused}
        onChange={(next) => void onToggle('guidelinesPaused', next)}
        disabled={targetIsAdmin || loading}
      />
      <Toggle
        label="event rqmt pause"
        checked={value.attendancePaused}
        onChange={(next) => void onToggle('attendancePaused', next)}
        disabled={targetIsAdmin || loading || value.guidelinesPaused}
      />
      {targetIsAdmin ? <p className="text-muted text-xs">admins can't be paused</p> : null}
      {initial.guidelinesPaused && !value.guidelinesPaused ? (
        <p className="text-muted text-xs">
          lifting this leaves an event rqmt pause until they check in and meet the event rqmt
        </p>
      ) : null}
      {confirmElement}
    </>
  );
}

function describeImpact(e: PauseImpactEvent): string {
  const when = e.startDatetime ? formatShortDateTime(e.startDatetime) : 'date tbd';
  return `• ${e.title.toLowerCase()} (${when}) — ${ROLE_LABEL[e.role]} · ${OUTCOME_LABEL[e.outcome]}`;
}
