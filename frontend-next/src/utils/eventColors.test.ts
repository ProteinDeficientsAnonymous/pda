import { describe, it, expect } from 'vitest';
import type { EventType, Visibility } from './eventColors';
import { getEventColors } from './eventColors';

function hexToHsl(hex: string): { h: number; s: number; l: number } {
  const clean = hex.replace(/^#/, '');
  const r = parseInt(clean.slice(0, 2), 16) / 255;
  const g = parseInt(clean.slice(2, 4), 16) / 255;
  const b = parseInt(clean.slice(4, 6), 16) / 255;
  const l = Math.max(r, g, b);
  const s = l - Math.min(r, g, b);
  const h = s === 0 ? 0 : l === r ? ((g - b) / s) % 6 : l === g ? 2 + (b - r) / s : 4 + (r - g) / s;
  return { h: h / 6, s: s / (1 - Math.abs(2 * l - 1)), l };
}

describe('getEventColors', () => {
  it('all four visibility choices produce distinct light colors', () => {
    const colors = new Set<string>();
    const combinations: [EventType, Visibility][] = [
      ['official', 'public'],
      ['community', 'public'],
      ['community', 'members_only'],
      ['community', 'invite_only'],
    ];
    for (const [eventType, visibility] of combinations) {
      const { bg } = getEventColors(eventType, visibility, 'light');
      colors.add(bg);
    }
    expect(colors.size).toBe(4);
  });

  it('all four visibility choices produce distinct dark colors', () => {
    const colors = new Set<string>();
    const combinations: [EventType, Visibility][] = [
      ['official', 'public'],
      ['community', 'public'],
      ['community', 'members_only'],
      ['community', 'invite_only'],
    ];
    for (const [eventType, visibility] of combinations) {
      const { bg } = getEventColors(eventType, visibility, 'dark');
      colors.add(bg);
    }
    expect(colors.size).toBe(4);
  });

  it('light mode has lighter backgrounds', () => {
    const { bg } = getEventColors('official', 'public', 'light');
    const hsl = hexToHsl(bg);
    expect(hsl.l).toBeGreaterThan(0.7);
  });

  it('dark mode has darker backgrounds', () => {
    const { bg: lightBg } = getEventColors('official', 'public', 'light');
    const { bg: darkBg } = getEventColors('official', 'public', 'dark');
    const lightL = hexToHsl(lightBg).l;
    const darkL = hexToHsl(darkBg).l;
    expect(darkL).toBeLessThan(lightL);
  });
});