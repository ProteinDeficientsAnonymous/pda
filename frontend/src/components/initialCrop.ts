// Initial crop geometry for ImageCropDialog. Kept separate from the component so
// it can be unit-tested directly (the component test mocks react-image-crop, so
// this math was previously unexercised — see issue 428).
//
// `width`/`height` are the *rendered* image dimensions in px — i.e. what the user
// actually sees. ImageCropDialog caps the rendered height at MAX_PREVIEW_PX by
// constraining the .ReactCrop element (not the wrapper), so the image is scaled
// down rather than clipped. That means the dimensions passed here always match the
// visible preview, and the crop never extends past it in any orientation. The
// returned crop is in percent units so it scales with the displayed image.

import { centerCrop, type PercentCrop } from 'react-image-crop';
import type { CropShape } from './ImageCropDialog';

// Max rendered preview height in px (20rem, matching the old Tailwind `max-h-80`).
// ImageCropDialog applies this as the maxHeight on the .ReactCrop element, so it's
// the single source of truth for how tall the preview can get.
export const MAX_PREVIEW_PX = 320;

// Fraction of the shorter edge the initial crop covers.
const INITIAL_FILL = 0.8;

export function initialCrop(width: number, height: number, shape: CropShape): PercentCrop {
  if (shape === 'round') {
    // 1:1 square sized off the SHORTER edge so it always fits inside the image,
    // regardless of orientation. Expressing the same pixel side as a percentage of
    // each axis keeps it square in pixel space (issue 428: sizing off width alone
    // made the square taller than landscape/pano images, so it got clamped into an
    // unmovable band).
    const side = INITIAL_FILL * Math.min(width, height);
    return centerCrop(
      { unit: '%', x: 0, y: 0, width: (side / width) * 100, height: (side / height) * 100 },
      width,
      height,
    );
  }

  // Rect (free-form): a flat 80% box on both axes. The rendered height is already
  // capped at MAX_PREVIEW_PX by the dialog, so 80% always lands inside the visible
  // preview — no per-orientation height compensation needed.
  return centerCrop(
    { unit: '%', x: 0, y: 0, width: INITIAL_FILL * 100, height: INITIAL_FILL * 100 },
    width,
    height,
  );
}
