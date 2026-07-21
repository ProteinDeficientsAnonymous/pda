import { fireEvent, render, screen, waitFor } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import type { ReactNode } from 'react';
import { beforeEach, describe, expect, it, vi } from 'vitest';

import { cropImage } from '@/utils/cropImage';

// react-image-crop uses pointer events + ResizeObserver that jsdom doesn't
// fully support. Stub it so it renders a simple sentinel element that
// still exposes the props we care about (circularCrop, aspect).
vi.mock('react-image-crop', () => ({
  default: ({
    circularCrop,
    aspect,
    children,
  }: {
    circularCrop?: boolean;
    aspect?: number;
    children?: ReactNode;
  }) => (
    <div
      data-testid="cropper"
      data-circular={String(Boolean(circularCrop))}
      data-aspect={String(aspect ?? '')}
    >
      {children}
    </div>
  ),
  centerCrop: (c: unknown) => c,
  makeAspectCrop: (_base: unknown, aspect: number, width: number, height: number) => {
    const cropW = Math.min(width, height * aspect);
    const cropH = cropW / aspect;
    return {
      unit: '%',
      x: 0,
      y: 0,
      width: (cropW / width) * 100,
      height: (cropH / height) * 100,
    };
  },
}));

// cropImage reaches into canvas APIs — stub it
vi.mock('@/utils/cropImage', () => ({
  cropImage: vi.fn().mockResolvedValue(new Blob(['img'], { type: 'image/png' })),
}));

import { ImageCropDialog } from './ImageCropDialog';

// jsdom doesn't implement createObjectURL/revokeObjectURL
beforeEach(() => {
  vi.stubGlobal('URL', {
    createObjectURL: vi.fn().mockReturnValue('blob:mock-url'),
    revokeObjectURL: vi.fn(),
  });
  vi.clearAllMocks();
});

function makeFile(name = 'photo.png') {
  return new File(['img-data'], name, { type: 'image/png' });
}

function renderDialog({
  shape = 'round' as 'round' | 'rect',
  onCancel = vi.fn(),
  onCrop = vi.fn(),
} = {}) {
  return render(
    <ImageCropDialog file={makeFile()} shape={shape} onCancel={onCancel} onCrop={onCrop} />,
  );
}

describe('ImageCropDialog', () => {
  it('renders in circle (round) mode with locked 1:1 aspect and action buttons', () => {
    renderDialog({ shape: 'round' });

    const dialog = screen.getByRole('dialog', { name: /crop photo/i });
    expect(dialog).toBeInTheDocument();

    const cropper = screen.getByTestId('cropper');
    expect(cropper).toHaveAttribute('data-circular', 'true');
    expect(cropper).toHaveAttribute('data-aspect', '1');
    expect(screen.getByRole('button', { name: /^cancel$/i })).toBeInTheDocument();
    expect(screen.getByRole('button', { name: /^save$/i })).toBeInTheDocument();
  });

  it('renders in rectangle (rect) mode locked to square by default, not circular', () => {
    renderDialog({ shape: 'rect' });

    const dialog = screen.getByRole('dialog', { name: /crop photo/i });
    expect(dialog).toBeInTheDocument();

    const cropper = screen.getByTestId('cropper');
    expect(cropper).toHaveAttribute('data-circular', 'false');
    expect(cropper).toHaveAttribute('data-aspect', '1');
    expect(screen.getByRole('button', { name: /^cancel$/i })).toBeInTheDocument();
    expect(screen.getByRole('button', { name: /^save$/i })).toBeInTheDocument();
  });

  it('offers a square / 4:5 shape toggle in rect mode and locks the chosen aspect', async () => {
    const user = userEvent.setup();
    renderDialog({ shape: 'rect' });

    const group = screen.getByRole('group', { name: /crop shape/i });
    expect(group).toBeInTheDocument();

    const square = screen.getByRole('button', { name: /^square$/i });
    const portrait = screen.getByRole('button', { name: /^4:5$/i });
    expect(square).toHaveAttribute('aria-pressed', 'true');
    expect(portrait).toHaveAttribute('aria-pressed', 'false');

    await user.click(portrait);

    expect(portrait).toHaveAttribute('aria-pressed', 'true');
    expect(square).toHaveAttribute('aria-pressed', 'false');
    expect(screen.getByTestId('cropper')).toHaveAttribute('data-aspect', '0.8');
  });

  it('saves the toggled square aspect even without dragging the crop (issue 598)', async () => {
    const user = userEvent.setup();
    const onCrop = vi.fn();
    renderDialog({ shape: 'rect', onCrop });

    const img = document.body.querySelector('img')!;
    Object.defineProperty(img, 'width', { value: 400, configurable: true });
    Object.defineProperty(img, 'height', { value: 500, configurable: true });
    Object.defineProperty(img, 'naturalWidth', { value: 400, configurable: true });
    Object.defineProperty(img, 'naturalHeight', { value: 500, configurable: true });
    fireEvent.load(img);

    expect(screen.getByRole('button', { name: /^4:5$/i })).toHaveAttribute('aria-pressed', 'true');

    await user.click(screen.getByRole('button', { name: /^square$/i }));
    await user.click(screen.getByRole('button', { name: /^save$/i }));

    expect(cropImage).toHaveBeenCalledOnce();
    const [, area] = vi.mocked(cropImage).mock.lastCall!;
    expect(area.width).toBeCloseTo(area.height);
  });

  it('enables save on image load without any drag or toggle', async () => {
    const user = userEvent.setup();
    const onCrop = vi.fn();
    renderDialog({ shape: 'rect', onCrop });

    const img = document.body.querySelector('img')!;
    Object.defineProperty(img, 'width', { value: 400, configurable: true });
    Object.defineProperty(img, 'height', { value: 500, configurable: true });
    Object.defineProperty(img, 'naturalWidth', { value: 400, configurable: true });
    Object.defineProperty(img, 'naturalHeight', { value: 500, configurable: true });
    fireEvent.load(img);

    const save = screen.getByRole('button', { name: /^save$/i });
    expect(save).toBeEnabled();
    await user.click(save);
    expect(cropImage).toHaveBeenCalledOnce();
  });

  it('surfaces an error and clears saving when cropping fails (issue 580)', async () => {
    const user = userEvent.setup();
    vi.mocked(cropImage).mockRejectedValueOnce(new Error('timed out processing image'));
    renderDialog({ shape: 'rect' });

    const img = document.body.querySelector('img')!;
    Object.defineProperty(img, 'width', { value: 400, configurable: true });
    Object.defineProperty(img, 'height', { value: 400, configurable: true });
    Object.defineProperty(img, 'naturalWidth', { value: 400, configurable: true });
    Object.defineProperty(img, 'naturalHeight', { value: 400, configurable: true });
    fireEvent.load(img);

    // Toggling an aspect populates `completed` (mock doesn't fire onComplete).
    await user.click(screen.getByRole('button', { name: /^square$/i }));
    await user.click(screen.getByRole('button', { name: /^save$/i }));

    await waitFor(() => {
      expect(screen.getByRole('alert')).toHaveTextContent(/couldn't process that photo/i);
    });
    expect(screen.getByRole('button', { name: /^save$/i })).toBeInTheDocument();
  });

  it('does not show the shape toggle in round mode', () => {
    renderDialog({ shape: 'round' });
    expect(screen.queryByRole('group', { name: /crop shape/i })).not.toBeInTheDocument();
  });

  it('cancel button calls onCancel callback', async () => {
    const onCancel = vi.fn();
    const user = userEvent.setup();
    renderDialog({ onCancel });

    await user.click(screen.getByRole('button', { name: /^cancel$/i }));

    expect(onCancel).toHaveBeenCalledOnce();
  });

  it('dialog container has role="dialog" and is accessible', () => {
    renderDialog();

    const dialog = screen.getByRole('dialog');
    expect(dialog).toBeInTheDocument();
    expect(dialog).toHaveAttribute('aria-modal', 'true');
    expect(dialog).toHaveAttribute('aria-label', 'crop photo');
  });
});
