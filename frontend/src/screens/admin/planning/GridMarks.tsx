import type { ReactElement } from 'react';

import { cn } from '@/utils/cn';

import { type CellState, STATE_TEXT } from './gridCell';
import type { SlotColumn } from './gridLayout';
import type { Coverage } from './gridSummary';
import { TileFace } from './GridTile';

const COVERAGE_TILE = { in: 'committed', sent: 'proposed', draft: 'draft' } as const;

function coverageText(coverage: Coverage): string {
  switch (coverage.kind) {
    case 'in':
    case 'sent':
    case 'draft':
      return STATE_TEXT[COVERAGE_TILE[coverage.kind]];
    case 'past':
      return 'past';
    case 'free':
      return `${String(coverage.count)} free`;
  }
}

function CoverageFace({ coverage }: { coverage: Coverage }): ReactElement {
  switch (coverage.kind) {
    case 'in':
    case 'sent':
    case 'draft':
      return <TileFace state={COVERAGE_TILE[coverage.kind]} />;
    case 'past':
      return (
        <span aria-hidden="true" className="text-muted font-normal">
          –
        </span>
      );
    case 'free':
      return (
        <span
          aria-hidden="true"
          className={cn(
            'flex h-[var(--pg-tile,15px)] min-w-[var(--pg-tile,15px)] items-center justify-center rounded-[3px]',
            coverage.count === 0 && 'bg-plan-ink text-plan-ink-fg',
          )}
        >
          {coverage.count}
        </span>
      );
  }
}

export function CoverageMark({ coverage }: { coverage: Coverage }) {
  return (
    <>
      <CoverageFace coverage={coverage} />
      <span className="sr-only">{coverageText(coverage)}</span>
    </>
  );
}

export function GridKey({ columns }: { columns: SlotColumn[] }) {
  const extras = columns.filter((c) => c.isExtra);
  return (
    <div className="text-muted mt-3 text-center text-xs">
      <ul className="flex flex-wrap justify-center gap-x-3 gap-y-1">
        {(Object.keys(STATE_TEXT) as CellState[]).map((state) => (
          <li key={state} className="flex items-center gap-1">
            <TileFace state={state} />
            {STATE_TEXT[state]}
          </li>
        ))}
      </ul>
      <p className="mt-1">monthlies: in / offered on their form</p>
      {extras.length > 0 ? (
        <p className="mt-1">{extras.map((c) => `${c.header} ${c.slot.label}`).join(' · ')}</p>
      ) : null}
    </div>
  );
}
