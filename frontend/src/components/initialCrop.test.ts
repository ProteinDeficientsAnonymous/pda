import { describe, expect, it } from 'vitest';

import {
  coverCrop,
  defaultCoverAspect,
  initialCrop,
  PORTRAIT_ASPECT,
  SQUARE_ASPECT,
} from './initialCrop';

// Regression for issue 428: the round crop was sized off image *width*, so for any
// non-portrait image the square was taller than the image and react-image-crop
// clamped it into an unmovable band. The crop must always fit inside the image.
// `width`/`height` are rendered preview dimensions, height-capped at 320 by the dialog.

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

function pixelAspect(crop: { width: number; height: number }, w: number, h: number): number {
  return ((crop.width / 100) * w) / ((crop.height / 100) * h);
}

describe('defaultCoverAspect', () => {
  it('picks square for landscape and square-ish images', () => {
    expect(defaultCoverAspect(800, 200)).toBe(SQUARE_ASPECT);
    expect(defaultCoverAspect(320, 320)).toBe(SQUARE_ASPECT);
    expect(defaultCoverAspect(320, 300)).toBe(SQUARE_ASPECT);
  });

  it('picks 4:5 for clearly portrait images', () => {
    expect(defaultCoverAspect(213, 320)).toBe(PORTRAIT_ASPECT);
    expect(defaultCoverAspect(400, 600)).toBe(PORTRAIT_ASPECT);
  });
});

describe('coverCrop', () => {
  const dims: [string, number, number][] = [
    ['landscape', 800, 200],
    ['square', 320, 320],
    ['portrait', 213, 320],
  ];

  it.each(dims)('produces a fitted, centered crop of the given aspect: %s', (_l, w, h) => {
    for (const aspect of [SQUARE_ASPECT, PORTRAIT_ASPECT]) {
      const crop = coverCrop(w, h, aspect);
      fits(crop);
      isCentered(crop);
      expect(pixelAspect(crop, w, h)).toBeCloseTo(aspect, 3);
    }
  });
});

describe('initialCrop — rect (event cover)', () => {
  it('defaults landscape photos to a square crop', () => {
    const w = 800;
    const h = 200;
    const crop = initialCrop(w, h, 'rect');
    fits(crop);
    isCentered(crop);
    expect(pixelAspect(crop, w, h)).toBeCloseTo(SQUARE_ASPECT, 3);
  });

  it('defaults tall photos to a 4:5 crop', () => {
    const w = 213;
    const h = 320;
    const crop = initialCrop(w, h, 'rect');
    fits(crop);
    isCentered(crop);
    expect(pixelAspect(crop, w, h)).toBeCloseTo(PORTRAIT_ASPECT, 3);
  });
});
