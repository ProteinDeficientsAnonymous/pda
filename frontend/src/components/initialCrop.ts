// Initial crop geometry for ImageCropDialog. `width`/`height` are the rendered
// (height-capped at MAX_PREVIEW_PX) image dimensions; returns percent units.

import { centerCrop, makeAspectCrop, type PercentCrop, type PixelCrop } from 'react-image-crop';

import type { CropShape } from './ImageCropDialog';

export const MAX_PREVIEW_PX = 320;

const INITIAL_FILL = 0.8;

export const SQUARE_ASPECT = 1;
export const PORTRAIT_ASPECT = 4 / 5;
export const COVER_ASPECTS = [SQUARE_ASPECT, PORTRAIT_ASPECT] as const;

// Landscape opens square, tall opens 4:5 — snap to whichever is closest.
export function defaultCoverAspect(width: number, height: number): number {
  const imageAspect = width / height;
  return COVER_ASPECTS.reduce((best, aspect) =>
    Math.abs(aspect - imageAspect) < Math.abs(best - imageAspect) ? aspect : best,
  );
}

export function initialCrop(width: number, height: number, shape: CropShape): PercentCrop {
  if (shape === 'round') {
    // Size off the shorter edge so the square fits in any orientation (issue 428:
    // sizing off width alone made it taller than landscape images and unmovable).
    const side = INITIAL_FILL * Math.min(width, height);
    return centerCrop(
      { unit: '%', x: 0, y: 0, width: (side / width) * 100, height: (side / height) * 100 },
      width,
      height,
    );
  }

  return coverCrop(width, height, defaultCoverAspect(width, height));
}

export function coverCrop(width: number, height: number, aspect: number): PercentCrop {
  return centerCrop(
    makeAspectCrop({ unit: '%', width: 100 }, aspect, width, height),
    width,
    height,
  );
}

export function percentToPixelCrop(pct: PercentCrop, width: number, height: number): PixelCrop {
  return {
    unit: 'px',
    x: (pct.x / 100) * width,
    y: (pct.y / 100) * height,
    width: (pct.width / 100) * width,
    height: (pct.height / 100) * height,
  };
}
