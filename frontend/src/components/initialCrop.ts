// Initial crop geometry for ImageCropDialog, split out so it can be unit-tested
// (the component test mocks react-image-crop). `width`/`height` are the *rendered*
// image dimensions; ImageCropDialog caps rendered height at MAX_PREVIEW_PX, so the
// inputs always match the visible preview. Returns percent units so the crop scales
// with the displayed image. See issue 428.

import { centerCrop, type PercentCrop } from 'react-image-crop';
import type { CropShape } from './ImageCropDialog';

// Max rendered preview height (20rem). The single source of truth for the cap;
// ImageCropDialog applies it as maxHeight on the .ReactCrop element.
export const MAX_PREVIEW_PX = 320;

// Fraction of the shorter edge the initial round crop covers (rect fills the image).
const INITIAL_FILL = 0.8;

export function initialCrop(width: number, height: number, shape: CropShape): PercentCrop {
  if (shape === 'round') {
    // 1:1 square sized off the SHORTER edge so it fits in any orientation. The same
    // pixel side as a percentage of each axis keeps it square in pixel space. (Issue
    // 428: sizing off width alone made the square taller than landscape/pano images,
    // clamping it into an unmovable band.)
    const side = INITIAL_FILL * Math.min(width, height);
    return centerCrop(
      { unit: '%', x: 0, y: 0, width: (side / width) * 100, height: (side / height) * 100 },
      width,
      height,
    );
  }

  // Rect (free-form): default to the whole image so the full photo is the initial
  // crop, matching the photo's own shape instead of an inset frame the user must
  // drag out to. Users can still drag the edges in to crop tighter. (Issue 514.)
  return centerCrop({ unit: '%', x: 0, y: 0, width: 100, height: 100 }, width, height);
}
