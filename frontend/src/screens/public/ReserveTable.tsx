import { format } from 'date-fns';

import { type ReserveEntry, useReserve } from '@/api/reserve';

function formatDollars(amount: number): string {
  return `$${Math.abs(amount).toLocaleString('en-US', {
    minimumFractionDigits: 2,
    maximumFractionDigits: 2,
  })}`;
}

function formatAmount(amount: number): string {
  return amount === 0 ? '—' : formatDollars(amount);
}

function formatSigned(amount: number): string {
  return `${amount < 0 ? '−' : '+'}${formatDollars(amount)}`;
}

function sum(entries: ReserveEntry[], pick: (e: ReserveEntry) => number): number {
  return Math.round(entries.reduce((total, e) => total + pick(e), 0) * 100) / 100;
}

const CELL = 'px-3 py-2';
const NUM_CELL = `${CELL} text-right tabular-nums whitespace-nowrap`;

export function ReserveTable() {
  const { data } = useReserve();
  if (!data || data.entries.length === 0) return null;

  const { entries, updatedAt } = data;
  const asOf = updatedAt ? ` (as of ${format(updatedAt, 'MMM d, yyyy').toLowerCase()})` : '';

  return (
    <section className="mt-10" aria-labelledby="reserve-heading">
      <h2 id="reserve-heading" className="mb-2 text-lg font-medium">
        financial breakdown
      </h2>
      <p className="text-muted mb-4 text-sm">
        events collect a per-person share for food and pay the restaurant — leftover mostly comes
        from folks who no-show or cancel late{asOf}
      </p>
      <div className="border-border bg-surface overflow-x-auto rounded-lg border">
        <table className="w-full text-left text-sm">
          <thead className="bg-background text-muted text-xs">
            <tr>
              <th className={CELL}>source</th>
              <th className={NUM_CELL}>collected</th>
              <th className={NUM_CELL}>paid out</th>
              <th className={NUM_CELL}>facilitator drinks</th>
              <th className={NUM_CELL}>left over</th>
            </tr>
          </thead>
          <tbody>
            {entries.map((entry) => (
              <tr key={entry.id} className="border-border border-t">
                <td className={`${CELL} min-w-52`}>{entry.label}</td>
                <td className={NUM_CELL}>{formatAmount(entry.collected)}</td>
                <td className={NUM_CELL}>{formatAmount(entry.paidOut)}</td>
                <td className={NUM_CELL}>{formatAmount(entry.facilitatorDrinks)}</td>
                <td className={NUM_CELL}>{formatSigned(entry.leftOver)}</td>
              </tr>
            ))}
          </tbody>
          <tfoot>
            <tr className="border-border border-t font-medium">
              <td className={CELL}>total</td>
              <td className={NUM_CELL} />
              <td className={NUM_CELL} />
              <td className={NUM_CELL}>
                {formatDollars(sum(entries, (e) => e.facilitatorDrinks))}
              </td>
              <td className={NUM_CELL}>{formatSigned(sum(entries, (e) => e.leftOver))}</td>
            </tr>
          </tfoot>
        </table>
      </div>
    </section>
  );
}
