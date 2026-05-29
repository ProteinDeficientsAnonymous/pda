# Fix 428 — profile picture crop forces image into fixed dimensions

## Symptom (from the issue + reporter)

> When I upload my current picture, it crops out the top of it, cutting off my head.
>
> it forces a photo into the dimensions and cuts off the rest so you cant select which
> part of the photo you want, you can only move the crop circle on the visible portion

- Route: `/profile` (avatar upload → `ImageCropDialog` in `round` mode)
- Reproduced on **both iPhone Safari and desktop** → not EXIF/touch-specific; it is a
  deterministic layout/geometry bug.

## Root cause (confirmed)

`ImageCropDialog.onImageLoad` builds the initial circular crop with:

```ts
centerCrop(makeAspectCrop({ unit: '%', width: 80 }, 1, width, height), width, height)
```

`makeAspectCrop` interprets `width: 80` as **80% of the image's width**, then sets the
square's height equal to that same pixel value (aspect 1:1). For any image that is **not
portrait** (landscape, square, panoramic), `0.8 × width` in pixels is **taller than the
image height**, so react-image-crop clamps the crop to the image bounds and anchors it.
With the aspect locked to 1:1, the user can no longer drag or resize the circle outside
that clamped band — exactly "you can only move the crop circle on the visible portion."

Verified two ways:

1. **Library source** (`react-image-crop` `makeAspectCrop`): width-basis sizing followed
   by a `t.y + t.height > n` clamp that shrinks + anchors the square.
2. **Visual repro** (headless Chrome, real `ReactCrop.css`, same wrapper/img classes):
   - portrait 3:4 → square fits (whole photo shown) ✓
   - square → square ≈ image, edges clamped
   - landscape 4:3 (4032×3024 → rendered 427×320) → 80%-width square = 342×342 **overflows
     the 320px-tall image** → clamped
   - wide pano (4032×1500 → 448×167) → square = 358×358, massively overflows → clamped

The rendered image itself is fully visible (object-fit is correct); the bug is purely the
**initial crop rectangle** being sized off the wrong axis.

## Fix

Size the initial 1:1 crop off the image's **shorter edge** so the square always fits
inside the image regardless of orientation, then center it. Extract the geometry into a
pure helper so it can be unit-tested (the current tests mock `makeAspectCrop`, so they
never exercised this math).

- New `initialCrop(width, height, shape)` helper returning a `PercentCrop`.
- `round`: square side = `80% of min(width, height)`, expressed as a percentage of each
  axis, centered.
- `rect`: keep existing behaviour (free-form, capped at preview height).
- Add unit tests for the helper across portrait / square / landscape / pano — assert the
  crop never exceeds 100% on either axis and stays centered.

## Out of scope (noted, not fixed here)

- Zoom / pan of the underlying image (the reporter's "select which part" wish beyond
  dragging the circle) would need a different cropper (e.g. react-easy-crop). This fix
  restores full drag freedom within the visible image, which resolves the reported defect.
