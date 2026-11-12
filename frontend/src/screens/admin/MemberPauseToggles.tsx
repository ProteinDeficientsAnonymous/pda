import { useState } from 'react';

import { Toggle } from '@/components/ui/Toggle';

import { usePauseConfirm } from './usePauseConfirm';

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
  const [initial] = useState(value);
  const { confirmPause, loading, element: confirmElement } = usePauseConfirm();

  async function onToggle(field: keyof PauseState, next: boolean) {
    // A guidelines pause replaces an event rqmt pause, so drop any pending event rqmt change.
    const base =
      field === 'guidelinesPaused'
        ? { ...value, attendancePaused: initial.attendancePaused }
        : value;
    if (!next || initial[field] || (await confirmPause(memberId, field))) {
      onChange({ ...base, [field]: next });
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
        disabled={targetIsAdmin || loading || value.guidelinesPaused || initial.attendancePaused}
      />
      {targetIsAdmin ? <p className="text-muted text-xs">admins can't be paused</p> : null}
      {initial.attendancePaused ? (
        <p className="text-muted text-xs">
          lifts when they check in at an official or club event and meet the event rqmt
        </p>
      ) : null}
      {initial.guidelinesPaused && !value.guidelinesPaused ? (
        <p className="text-muted text-xs">
          lifting this leaves an event rqmt pause until they check in and meet the event rqmt
        </p>
      ) : null}
      {confirmElement}
    </>
  );
}
