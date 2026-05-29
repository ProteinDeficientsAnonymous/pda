import { describe, it, expect } from 'vitest';
import { initialCrop } from './initialCrop';

// Regression for issue 428: the round (1:1) crop was sized as 80% of the image
// *width*, so for any non-portrait image the square was taller than the image and
// react-image-crop clamped it into an unmovable band ("you can only move the crop
// circle on the visible portion"). The crop must always fit inside the image.

function fits(crop: { x: number; y: number; width: number; height: number }) {
  expect(crop.x).toBeGreaterThanOrEqual(0);
  expect(crop.y).toBeGreaterThanOrEqual(0);
  expect(crop.x + crop.width).toBeLessThanOrEqual(100 + 1e-6);
  expect(crop.y + crop.height).toBeLessThanOrEqual(100 + 1e-6);
}

function isCentered(crop: { x: number; y: number; width: number; height: number }) {
  expect(crop.x).toBeCloseTo((100 - crop.width) / 2, 4);
  expect(crop.y).toBeCloseTo((100 - crop.height) / 2, 4);
}

describe('initialCrop — round (1:1)', () => {
  const cases: [string, number, number][] = [
    ['portrait 3:4', 240, 320],
    ['square', 320, 320],
    ['landscape 4:3', 427, 320],
    ['wide pano', 448, 167],
    ['tall strip', 100, 600],
  ];

  it.each(cases)('fits inside the image and stays centered: %s', (_label, w, h) => {
    const crop = initialCrop(w, h, 'round');
    expect(crop.unit).toBe('%');
    fits(crop);
    isCentered(crop);
  });

  it('produces a true 1:1 square in pixel space', () => {
    // landscape: 80% of the short edge (height) = 256px square.
    const w = 427;
    const h = 320;
    const crop = initialCrop(w, h, 'round');
    const pxW = (crop.width / 100) * w;
    const pxH = (crop.height / 100) * h;
    expect(pxW).toBeCloseTo(pxH, 2);
    expect(pxH).toBeCloseTo(0.8 * Math.min(w, h), 2);
  });

  it('sizes off the shorter edge for portrait too', () => {
    const w = 240;
    const h = 320;
    const crop = initialCrop(w, h, 'round');
    const pxW = (crop.width / 100) * w;
    expect(pxW).toBeCloseTo(0.8 * Math.min(w, h), 2);
  });
});

describe('initialCrop — rect (free-form)', () => {
  it('caps initial height at the visible preview, never overflowing', () => {
    // very tall image: rendered preview is capped at 320px, natural is 3000px tall
    const crop = initialCrop(2000, 3000, 'rect');
    fits(crop);
    expect(crop.width).toBe(80);
  });

  it('uses a plain 80% box when the image is not taller than the preview', () => {
    const crop = initialCrop(800, 200, 'rect');
    fits(crop);
    expect(crop.width).toBe(80);
    expect(crop.height).toBe(80);
  });
});
