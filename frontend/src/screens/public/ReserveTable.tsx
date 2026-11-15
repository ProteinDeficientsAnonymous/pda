interface ReserveRow {
  source: string;
  collectedCents: number;
  paidOutCents: number;
  facilitatorDrinksCents: number;
}

const RESERVE_AS_OF = 'nov 15, 2026';

const RESERVE_ROWS: ReserveRow[] = [
  {
    source: '4/25 brooklyn bridge park walk + cloudy donuts',
    collectedCents: 35000,
    paidOutCents: 26547,
    facilitatorDrinksCents: 1050,
  },
  {
    source: '5/9 spicy moon brunch',
    collectedCents: 144000,
    paidOutCents: 147964,
    facilitatorDrinksCents: 0,
  },
  {
    source: "5/24 hudson walk + jerrell's burgers",
    collectedCents: 38908,
    paidOutCents: 37283,
    facilitatorDrinksCents: 0,
  },
  {
    source: '6/21 central park walk + crunchwraps',
    collectedCents: 46100,
    paidOutCents: 41649,
    facilitatorDrinksCents: 0,
  },
  {
    source: "7/26 prospect park walk + flava's pizza",
    collectedCents: 22000,
    paidOutCents: 19085,
    facilitatorDrinksCents: 0,
  },
  {
    source: '8/15 brooklyn bridge walk + empanadas',
    collectedCents: 20800,
    paidOutCents: 14800,
    facilitatorDrinksCents: 875,
  },
  {
    source: '8/29 amituofo',
    collectedCents: 22000,
    paidOutCents: 20000,
    facilitatorDrinksCents: 0,
  },
  {
    source: '9/12 hudson river walk + peacefood',
    collectedCents: 31500,
    paidOutCents: 28868,
    facilitatorDrinksCents: 0,
  },
  {
    source: '10/17 prospect park walk + electric beets',
    collectedCents: 25200,
    paidOutCents: 23532,
    facilitatorDrinksCents: 1500,
  },
  {
    source: '11/14 central park walk',
    collectedCents: 19000,
    paidOutCents: 17000,
    facilitatorDrinksCents: 0,
  },
  {
    source: 'donation (cash app)',
    collectedCents: 2500,
    paidOutCents: 0,
    facilitatorDrinksCents: 0,
  },
  {
    source: 'donation (gofundme)',
    collectedCents: 3000,
    paidOutCents: 0,
    facilitatorDrinksCents: 0,
  },
  {
    source: 'website hosting, mar–oct',
    collectedCents: 0,
    paidOutCents: 6241,
    facilitatorDrinksCents: 0,
  },
  { source: 'stickers', collectedCents: 0, paidOutCents: 10365, facilitatorDrinksCents: 0 },
];

function leftoverCents(row: ReserveRow): number {
  return row.collectedCents - row.paidOutCents - row.facilitatorDrinksCents;
}

function formatCents(cents: number): string {
  return `$${(Math.abs(cents) / 100).toLocaleString('en-US', { minimumFractionDigits: 2 })}`;
}

function formatAmount(cents: number): string {
  return cents === 0 ? '—' : formatCents(cents);
}

function formatSigned(cents: number): string {
  return `${cents < 0 ? '−' : '+'}${formatCents(cents)}`;
}

const CELL = 'px-3 py-2';
const NUM_CELL = `${CELL} text-right tabular-nums whitespace-nowrap`;

export function ReserveTable() {
  const totalDrinks = RESERVE_ROWS.reduce((sum, r) => sum + r.facilitatorDrinksCents, 0);
  const totalLeftover = RESERVE_ROWS.reduce((sum, r) => sum + leftoverCents(r), 0);

  return (
    <section className="mt-10" aria-labelledby="reserve-heading">
      <h2 id="reserve-heading" className="mb-2 text-lg font-medium">
        where our reserve comes from
      </h2>
      <p className="text-muted mb-4 text-sm">
        events collect a per-person share for food and pay the restaurant — leftover mostly comes
        from folks who no-show or cancel late (as of {RESERVE_AS_OF})
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
            {RESERVE_ROWS.map((row) => (
              <tr key={row.source} className="border-border border-t">
                <td className={`${CELL} min-w-52`}>{row.source}</td>
                <td className={NUM_CELL}>{formatAmount(row.collectedCents)}</td>
                <td className={NUM_CELL}>{formatAmount(row.paidOutCents)}</td>
                <td className={NUM_CELL}>{formatAmount(row.facilitatorDrinksCents)}</td>
                <td className={NUM_CELL}>{formatSigned(leftoverCents(row))}</td>
              </tr>
            ))}
          </tbody>
          <tfoot>
            <tr className="border-border border-t font-medium">
              <td className={CELL}>total</td>
              <td className={NUM_CELL} />
              <td className={NUM_CELL} />
              <td className={NUM_CELL}>{formatCents(totalDrinks)}</td>
              <td className={NUM_CELL}>{formatSigned(totalLeftover)}</td>
            </tr>
          </tfoot>
        </table>
      </div>
    </section>
  );
}
