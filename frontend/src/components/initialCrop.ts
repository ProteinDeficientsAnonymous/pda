// Initial crop geometry for ImageCropDialog. Kept separate from the component so
// it can be unit-tested directly (the component test mocks react-image-crop, so
// this math was previously unexercised — see issue 428).
//
// `width`/`height` are the *rendered* image dimensions in px (the CSS-constrained
// preview, capped at MAX_PREVIEW_PX tall). The returned crop is in percent units
// so it scales with the displayed image.

import { centerCrop, type PercentCrop } from 'react-image-crop';
import type { CropShape } from './ImageCropDialog';

// Tailwind `max-h-80` → 20rem → 320px. The preview <img> is capped at this height,
// so initial crop math must respect it to avoid overshooting the visible image.
export const MAX_PREVIEW_PX = 320;

// Fraction of the available space the initial crop covers.
const INITIAL_FILL = 0.8;

export function initialCrop(width: number, height: number, shape: CropShape): PercentCrop {
  if (shape === 'round') {
    // 1:1 square sized off the SHORTER edge so it always fits inside the image,
    // regardless of orientation. Expressing the same pixel side as a percentage of
    // each axis keeps it square in pixel space (issue 428: sizing off width alone
    // made the square taller than landscape/pano images, so it got clamped into an
    // unmovable band).
    const side = INITIAL_FILL * Math.min(width, height);
    const widthPct = (side / width) * 100;
    const heightPct = (side / height) * 100;
    return centerCrop({ unit: '%', x: 0, y: 0, width: widthPct, height: heightPct }, width, height);
  }

  // Rect (free-form): the image is constrained to MAX_PREVIEW_PX in CSS, so a flat
  // 80%-of-natural crop can overshoot the visible image when the photo is portrait or
  // otherwise taller than the container. Cap the initial crop height at the rendered
  // preview height instead.
  const previewHeight = Math.min(height, MAX_PREVIEW_PX);
  const heightPct = Math.min(INITIAL_FILL * 100, (previewHeight / height) * INITIAL_FILL * 100);
  return centerCrop(
    { unit: '%', x: 0, y: 0, width: INITIAL_FILL * 100, height: heightPct },
    width,
    height,
  );
}
