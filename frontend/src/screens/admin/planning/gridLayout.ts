import type { PlanningSlot } from '@/api/planning';

export const EXTRA_MARKERS = ['★', '◆', '▲', '●'] as const;

const NAME_PX = 54;
const COLUMN_PX = 17;
const QUARTER_GAP_PX = 5;
const EXTRA_GAP_PX = 8;
const LOAD_PX = 26;

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
  extras.forEach((slot, i) => {
    if (i === 0 && columns.length > 0) track += 1;
    columns.push({ slot, header: EXTRA_MARKERS[i] ?? String(i + 1), isExtra: true, track });
    track += 1;
  });
  return columns;
}

export function gridTemplate(columns: SlotColumn[]): string {
  const tracks = [`${String(NAME_PX)}px`];
  let next = 2;
  for (const column of columns) {
    if (column.track > next) {
      tracks.push(`${String(column.isExtra ? EXTRA_GAP_PX : QUARTER_GAP_PX)}px`);
    }
    tracks.push(`${String(COLUMN_PX)}px`);
    next = column.track + 1;
  }
  tracks.push(`${String(LOAD_PX)}px`);
  return tracks.join(' ');
}

export function loadTrack(columns: SlotColumn[]): number {
  const last = columns[columns.length - 1];
  return last ? last.track + 1 : 2;
}
