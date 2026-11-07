import { useState } from 'react';
import { toast } from 'sonner';

import { fetchAttendancePausePreview, type PauseImpactEvent } from '@/api/attendancePausePreview';
import { Toggle } from '@/components/ui/Toggle';

import { AttendancePausePreviewDialog } from './AttendancePausePreviewDialog';

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
  const [affected, setAffected] = useState<PauseImpactEvent[] | null>(null);

  function setAttendancePaused(attendancePaused: boolean) {
    onChange({ ...value, attendancePaused });
  }

  async function onAttendanceToggle(next: boolean) {
    if (!next) {
      setAttendancePaused(false);
      return;
    }
    setLoading(true);
    try {
      const events = await fetchAttendancePausePreview(memberId);
      if (events.length === 0) setAttendancePaused(true);
      else setAffected(events);
    } catch {
      toast.error("couldn't load their upcoming events — try again");
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
        disabled={targetIsAdmin}
      />
      <Toggle
        label="event rqmt pause"
        checked={value.attendancePaused}
        onChange={(next) => void onAttendanceToggle(next)}
        disabled={targetIsAdmin || loading}
      />
      {targetIsAdmin ? <p className="text-muted text-xs">admins can't be paused</p> : null}
      {affected ? (
        <AttendancePausePreviewDialog
          events={affected}
          onCancel={() => {
            setAffected(null);
          }}
          onConfirm={() => {
            setAffected(null);
            setAttendancePaused(true);
          }}
        />
      ) : null}
    </>
  );
}
