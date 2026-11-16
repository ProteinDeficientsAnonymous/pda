import { useId } from 'react';

import { cn } from '@/utils/cn';

import { cellActionLabel, type CellState, isWithdrawable, STATE_TEXT } from './gridCell';

const TILE_CLASS: Record<CellState, string> = {
  committed: 'rounded-[3px] bg-plan-in text-plan-in-fg',
  proposed: 'rounded-full bg-plan-sent text-plan-sent-fg',
  draft: 'rounded-[3px] border border-dashed border-plan-draft bg-surface',
  declined: 'rounded-[3px] bg-plan-blank text-muted',
  available: 'rounded-[3px] border border-plan-free-edge bg-plan-free',
  blank: 'rounded-[3px] bg-plan-blank',
};

const GLYPH: Partial<Record<CellState, string>> = {
  committed: '✓',
  proposed: '?',
  declined: '✕',
};

export function TileFace({ state }: { state: CellState }) {
  return (
    <span
      aria-hidden="true"
      className={cn(
        'flex size-[var(--pg-tile,15px)] shrink-0 items-center justify-center text-[10px] leading-none font-bold md:text-sm',
        TILE_CLASS[state],
      )}
    >
      {GLYPH[state]}
      {state === 'available' ? (
        <span className="bg-plan-free-dot size-1.5 rounded-full md:size-2.5" />
      ) : null}
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
      className="focus-visible:outline-plan-ink enabled:hover:bg-surface-dim relative inline-flex h-[var(--pg-row)] w-[var(--pg-col)] items-center justify-center rounded focus-visible:z-10 focus-visible:outline-2 disabled:opacity-50"
    >
      <TileFace state={state} />
      <span id={textId} className="sr-only">
        {STATE_TEXT[state]}
        {blockedReason ? ` · ${blockedReason}` : null}
      </span>
    </button>
  );
}
