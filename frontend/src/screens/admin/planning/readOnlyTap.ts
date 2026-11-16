import type { CellState } from './gridCell';

export interface TapNotice {
  message: string;
  toAvailability: boolean;
}

export function readOnlyTapNotice(
  state: CellState,
  self: boolean,
  submitted: boolean,
  slotLabel: string,
): TapNotice | null {
  if (!self) return { message: 'you can only change your own row', toAvailability: false };
  if (state === 'proposed') return null;
  if (state === 'committed') {
    return {
      message: `you're in for ${slotLabel} — back out from my events`,
      toAvailability: false,
    };
  }
  if (state === 'blank') {
    return {
      message: submitted
        ? `you said you're not free in ${slotLabel} — update your availability`
        : 'add your availability so you can be proposed months',
      toAvailability: true,
    };
  }
  if (state === 'declined') {
    return {
      message: `you declined ${slotLabel} — ask a coordinator to propose you again`,
      toAvailability: false,
    };
  }
  return {
    message: "you can only put yourself in for months you've been proposed for",
    toAvailability: false,
  };
}
