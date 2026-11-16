import type { SummaryCounts } from './gridSummary';

const PILLS: { key: keyof SummaryCounts; label: string }[] = [
  { key: 'needPlanner', label: 'need a planner' },
  { key: 'waiting', label: 'waiting' },
  { key: 'noForm', label: 'no form' },
];

export function SummaryPills({ counts }: { counts: SummaryCounts }) {
  return (
    <div className="mb-3 flex flex-wrap gap-2">
      {PILLS.map(({ key, label }) => (
        <span
          key={key}
          className="border-border bg-surface text-foreground-secondary inline-flex items-center gap-1 rounded-full border px-3 py-1 text-xs"
        >
          <span className="text-foreground font-semibold">{counts[key]}</span> <span>{label}</span>
        </span>
      ))}
    </div>
  );
}
