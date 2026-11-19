import type { PlanningSlot } from '@/api/planning';

export const EXTRA_MARKERS = ['★', '◆', '▲', '●'] as const;
const MONTH_MARKERS: Partial<Record<number, string>> = { 6: '🥳', 12: '🎄' };

export const GRID_SIZE_CLASS =
  '[--pg-name:44px] [--pg-col:17px] [--pg-row:22px] [--pg-tile:15px] [--pg-qgap:5px] [--pg-xgap:8px] [--pg-load:26px] [--pg-bi:12px] ' +
  'md:[--pg-name:150px] md:[--pg-col:30px] md:[--pg-row:34px] md:[--pg-tile:24px] md:[--pg-qgap:10px] md:[--pg-xgap:16px] md:[--pg-load:64px] md:[--pg-bi:56px]';

export interface SlotColumn {
  slot: PlanningSlot;
  header: string;
  isExtra: boolean;
  track: number;
}

const byMonthThenOrder = (a: PlanningSlot, b: PlanningSlot) =>
  a.month - b.month || a.order - b.order;

const quarter = (month: number) => Math.floor((month - 1) / 3);

export function slotColumns(slots: PlanningSlot[]): SlotColumn[] {
  const monthlies = slots.filter((s) => s.kind === 'monthly').sort(byMonthThenOrder);
  const extras = slots.filter((s) => s.kind !== 'monthly').sort(byMonthThenOrder);

  let track = 2;
  const columns: SlotColumn[] = [];
  monthlies.forEach((slot, i) => {
    const prev = monthlies[i - 1];
    if (prev && quarter(prev.month) !== quarter(slot.month)) track += 1;
    columns.push({ slot, header: 'jfmamjjasond'[slot.month - 1] ?? '', isExtra: false, track });
    track += 1;
  });
  let markerIndex = 0;
  extras.forEach((slot, i) => {
    if (i === 0 && columns.length > 0) track += 1;
    const header = MONTH_MARKERS[slot.month] ?? EXTRA_MARKERS[markerIndex++] ?? String(i + 1);
    columns.push({ slot, header, isExtra: true, track });
    track += 1;
  });
  return columns;
}

export function gridTemplate(columns: SlotColumn[]): string {
  const tracks = ['var(--pg-name)'];
  let next = 2;
  for (const column of columns) {
    if (column.track > next) {
      tracks.push(column.isExtra ? 'var(--pg-xgap)' : 'var(--pg-qgap)');
    }
    tracks.push('var(--pg-col)');
    next = column.track + 1;
  }
  tracks.push('var(--pg-load)', 'var(--pg-bi)');
  return tracks.join(' ');
}

export function loadTrack(columns: SlotColumn[]): number {
  const last = columns[columns.length - 1];
  return last ? last.track + 1 : 2;
}

export function biTrack(columns: SlotColumn[]): number {
  return loadTrack(columns) + 1;
}
