import React from 'react';
import { render, screen } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { describe, it, expect, vi, beforeEach } from 'vitest';

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
    children?: React.ReactNode;
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
  makeAspectCrop: () => ({ unit: '%', x: 0, y: 0, width: 80, height: 80 }),
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
    <ImageCropDialog
      file={makeFile()}
      shape={shape}
      onCancel={onCancel}
      onCrop={onCrop}
    />,
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

  it('renders in rectangle (rect) mode as free-form (no aspect lock)', () => {
    renderDialog({ shape: 'rect' });

    const dialog = screen.getByRole('dialog', { name: /crop photo/i });
    expect(dialog).toBeInTheDocument();

    const cropper = screen.getByTestId('cropper');
    expect(cropper).toHaveAttribute('data-circular', 'false');
    expect(cropper).toHaveAttribute('data-aspect', '');
    expect(screen.getByRole('button', { name: /^cancel$/i })).toBeInTheDocument();
    expect(screen.getByRole('button', { name: /^save$/i })).toBeInTheDocument();
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
