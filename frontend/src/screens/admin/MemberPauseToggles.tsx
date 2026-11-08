import { Toggle } from '@/components/ui/Toggle';

export interface PauseState {
  isPaused: boolean;
  attendancePaused: boolean;
}

interface Props {
  value: PauseState;
  onChange: (next: PauseState) => void;
  targetIsAdmin: boolean;
}

export function MemberPauseToggles({ value, onChange, targetIsAdmin }: Props) {
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
        onChange={(attendancePaused) => {
          onChange({ ...value, attendancePaused });
        }}
        disabled={targetIsAdmin}
      />
      {targetIsAdmin ? <p className="text-muted text-xs">admins can't be paused</p> : null}
    </>
  );
}
