import type { CSSProperties } from 'react';

import type { BiannualInterest, PlannerColumn } from '@/api/planning';
import { cn } from '@/utils/cn';

import type { plannerLoad } from './gridSummary';

function Flag({ mark, words }: { mark: string; words: string }) {
  return (
    <>
      <span aria-hidden="true" className="text-muted shrink-0 text-[9px] md:text-[11px]">
        {mark}
      </span>
      <span className="sr-only">{words}</span>
    </>
  );
}

export function NameCell({ planner, style }: { planner: PlannerColumn; style: CSSProperties }) {
  return (
    <div
      style={style}
      title={planner.name}
      className={cn(
        'flex min-w-0 items-center gap-0.5 pr-1 text-xs md:gap-1 md:pr-2 md:text-sm',
        (!planner.isPlanner || !planner.submitted) && 'text-muted',
        !planner.submitted && 'italic',
      )}
    >
      <span className="truncate">{planner.name}</span>
      {planner.isPlanner ? null : <Flag mark="(left)" words="no longer a planner" />}
      {planner.hasEmail ? null : <Flag mark="✉✕" words="no email" />}
    </div>
  );
}

export function LoadCell({
  load,
  style,
}: {
  load: ReturnType<typeof plannerLoad>;
  style: CSSProperties;
}) {
  return (
    <div
      style={style}
      className="flex items-center justify-end text-[10px] tabular-nums md:text-xs"
    >
      {load ? (
        <>
          <span aria-hidden="true" className={cn(load.taken > load.offered && 'font-semibold')}>
            {`${String(load.taken)}/${String(load.offered)}`}
          </span>
          <span className="sr-only">
            {`${String(load.taken)} of ${String(load.offered)} taken${load.taken > load.offered ? ', over' : ''}`}
          </span>
        </>
      ) : (
        <>
          <span aria-hidden="true" className="text-muted">
            –
          </span>
          <span className="sr-only">no form</span>
        </>
      )}
    </div>
  );
}

export function PhoneShort({ short, long }: { short: string; long: string }) {
  return (
    <>
      <span className="md:hidden">{short}</span>
      <span className="hidden md:inline">{long}</span>
    </>
  );
}

export function BiCell({
  interest,
  style,
}: {
  interest: BiannualInterest | null;
  style: CSSProperties;
}) {
  return (
    // relative + overflow-hidden: the last column's 1px sr-only box would widen the scroller
    <div
      style={style}
      className={cn(
        'relative flex items-center justify-end overflow-hidden text-[10px] md:text-xs',
        (interest ?? 'no') === 'no' && 'text-muted',
      )}
    >
      <span aria-hidden="true">
        {interest ? <PhoneShort short={interest.charAt(0)} long={interest} /> : '–'}
      </span>
      <span className="sr-only">{`biannual: ${interest ?? 'no answer'}`}</span>
    </div>
  );
}
