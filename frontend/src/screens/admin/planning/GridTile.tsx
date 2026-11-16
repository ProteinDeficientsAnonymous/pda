import { useId } from 'react';

import { cn } from '@/utils/cn';

import { cellActionLabel, type CellState, isWithdrawable, STATE_TEXT } from './gridCell';

const TILE_CLASS: Record<CellState, string> = {
  committed: 'rounded-sm bg-plan-in text-plan-in-fg',
  proposed: 'rounded-full bg-plan-sent text-plan-sent-fg',
  no_answer: 'rounded-full bg-plan-sent text-plan-sent-fg',
  draft: 'rounded-sm border border-dashed border-plan-draft bg-surface',
  declined: 'rounded-sm bg-plan-blank text-plan-ink',
  available: 'rounded-sm border border-plan-free-edge bg-plan-free',
  blank: 'rounded-sm bg-plan-blank',
};

const GLYPH: Partial<Record<CellState, string>> = {
  committed: '✓',
  proposed: '?',
  no_answer: '!',
  declined: '✕',
};

export function TileFace({ state }: { state: CellState }) {
  return (
    <span
      aria-hidden="true"
      className={cn(
        'flex size-[15px] shrink-0 items-center justify-center text-[10px] leading-none font-bold',
        TILE_CLASS[state],
      )}
    >
      {GLYPH[state]}
      {state === 'available' ? <span className="bg-plan-free-dot size-1.5 rounded-full" /> : null}
    </span>
  );
}

interface GridTileProps {
  state: CellState;
  plannerName: string;
  slotLabel: string;
  isPlanner: boolean;
  disabled: boolean;
  onAct: () => void;
}

export function GridTile({
  state,
  plannerName,
  slotLabel,
  isPlanner,
  disabled,
  onAct,
}: GridTileProps) {
  const textId = useId();
  const blockedReason = !isWithdrawable(state) && !isPlanner ? 'no longer a planner' : null;
  return (
    <button
      type="button"
      aria-label={cellActionLabel(state, plannerName, slotLabel)}
      aria-describedby={textId}
      title={blockedReason ?? undefined}
      disabled={disabled || blockedReason !== null}
      onClick={onAct}
      className="focus-visible:outline-plan-ink relative inline-flex h-[22px] w-[17px] items-center justify-center rounded focus-visible:outline-2 disabled:opacity-50"
    >
      <TileFace state={state} />
      <span id={textId} className="sr-only">
        {STATE_TEXT[state]}
        {blockedReason ? ` · ${blockedReason}` : null}
      </span>
    </button>
  );
}
