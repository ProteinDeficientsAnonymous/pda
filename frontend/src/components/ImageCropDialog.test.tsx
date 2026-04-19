import React from 'react';
import { render, screen } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { describe, it, expect, vi, beforeEach } from 'vitest';

// react-easy-crop manipulates DOM dimensions that jsdom doesn't support.
// Stub it so it renders a simple sentinel element.
vi.mock('react-easy-crop', () => ({
  default: ({ cropShape }: { cropShape?: string }) => (
    <div data-testid="cropper" data-crop-shape={cropShape} />
  ),
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
  it('renders in circle (round) mode with crop photo label and action buttons', () => {
    renderDialog({ shape: 'round' });

    const dialog = screen.getByRole('dialog', { name: /crop photo/i });
    expect(dialog).toBeInTheDocument();

    expect(screen.getByTestId('cropper')).toHaveAttribute('data-crop-shape', 'round');
    expect(screen.getByRole('button', { name: /^cancel$/i })).toBeInTheDocument();
    expect(screen.getByRole('button', { name: /^save$/i })).toBeInTheDocument();
  });

  it('renders in rectangle (rect) mode with action buttons', () => {
    renderDialog({ shape: 'rect' });

    const dialog = screen.getByRole('dialog', { name: /crop photo/i });
    expect(dialog).toBeInTheDocument();

    expect(screen.getByTestId('cropper')).toHaveAttribute('data-crop-shape', 'rect');
    expect(screen.getByRole('button', { name: /^cancel$/i })).toBeInTheDocument();
    expect(screen.getByRole('button', { name: /^save$/i })).toBeInTheDocument();
  });

  it('renders zoom slider helper', () => {
    renderDialog();

    // The zoom label and range input are present
    expect(screen.getByRole('slider', { name: /zoom/i })).toBeInTheDocument();
    expect(screen.getByText('zoom')).toBeInTheDocument();
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
