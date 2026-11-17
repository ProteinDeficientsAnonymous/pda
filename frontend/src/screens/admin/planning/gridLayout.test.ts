import { describe, expect, it } from 'vitest';

import { makeSlot } from '@/test/fixtures';

import { biTrack, GRID_SIZE_CLASS, gridTemplate, loadTrack, slotColumns } from './gridLayout';

const monthly = (month: number, label = `m${String(month)}`) =>
  makeSlot({ id: label, label, month, order: month });
const extra = (id: string, month: number, order = 0) =>
  makeSlot({ id, label: id, month, order, kind: 'biannual' });

const vars = (names: string) =>
  names
    .split(' ')
    .map((name) => `var(--pg-${name})`)
    .join(' ');

const NAMED: Record<number, string> = { 0: 'january', 3: 'april', 11: 'december' };

const defaultYear = () => [
  ...Array.from({ length: 12 }, (_, i) => monthly(i + 1, NAMED[i] ?? `m${String(i + 1)}`)),
  extra('june anniversary', 6),
  extra('dec holiday', 12),
];

describe('slotColumns', () => {
  it('headers: month initials then extra markers', () => {
    expect(slotColumns(defaultYear()).map((c) => c.header)).toEqual([
      ...'jfmamjjasond'.split(''),
      '🥳',
      '🎄',
    ]);
  });

  it('marks june and december extras with emoji and keeps the other markers in order', () => {
    const cols = slotColumns([
      extra('dec', 12),
      extra('spring', 3),
      extra('june', 6),
      extra('fall', 9),
    ]);
    expect(cols.map((c) => c.header)).toEqual(['★', '🥳', '◆', '🎄']);
  });

  it('tracks skip quarter and extra gap tracks', () => {
    const cols = slotColumns(defaultYear());
    const track = (id: string) => cols.find((c) => c.slot.id === id)?.track;
    expect(track('january')).toBe(2);
    expect(track('april')).toBe(6);
    expect(track('december')).toBe(16);
    expect(track('june anniversary')).toBe(18);
    expect(track('dec holiday')).toBe(19);
    expect(loadTrack(cols)).toBe(20);
    expect(biTrack(cols)).toBe(21);
  });

  it('sorts input by month then order', () => {
    const cols = slotColumns([extra('b', 12), monthly(3, 'mar'), extra('a', 6), monthly(1, 'jan')]);
    expect(cols.map((c) => c.slot.id)).toEqual(['jan', 'mar', 'a', 'b']);
  });

  it('numbers extras past four', () => {
    const extras = Array.from({ length: 6 }, (_, i) => extra(`e${String(i)}`, 3, i));
    const cols = slotColumns(extras);
    expect(cols.map((c) => c.header)).toEqual(['★', '◆', '▲', '●', '5', '6']);
    expect(gridTemplate(cols)).toBe(vars('name col col col col col col load bi'));
  });

  it('keeps two june slots adjacent with the same header', () => {
    const cols = slotColumns([monthly(6, 'j1'), monthly(6, 'j2')]);
    expect(cols.map((c) => c.header)).toEqual(['j', 'j']);
    expect(cols.map((c) => c.track)).toEqual([2, 3]);
  });
});

describe('gridTemplate', () => {
  it('lays out name, columns, gaps, load and bi tracks', () => {
    const quarter = 'col col col';
    expect(gridTemplate(slotColumns(defaultYear()))).toBe(
      vars(`name ${quarter} qgap ${quarter} qgap ${quarter} qgap ${quarter} xgap col col load bi`),
    );
  });

  it('omits the extras gap when there are no extras', () => {
    const template = gridTemplate(slotColumns([monthly(1), monthly(2)]));
    expect(template).toBe(vars('name col col load bi'));
    expect(template).not.toContain('xgap');
  });
});

describe('GRID_SIZE_CLASS', () => {
  it('keeps phone sizes and scales every track up from md', () => {
    const classes = GRID_SIZE_CLASS.split(' ');
    expect(classes).toEqual(
      expect.arrayContaining([
        '[--pg-name:44px]',
        '[--pg-col:17px]',
        '[--pg-row:22px]',
        '[--pg-bi:12px]',
      ]),
    );
    for (const name of ['name', 'col', 'row', 'tile', 'qgap', 'xgap', 'load', 'bi']) {
      expect(classes.filter((c) => c.startsWith(`[--pg-${name}:`))).toHaveLength(1);
      expect(classes.filter((c) => c.startsWith(`md:[--pg-${name}:`))).toHaveLength(1);
    }
  });
});
