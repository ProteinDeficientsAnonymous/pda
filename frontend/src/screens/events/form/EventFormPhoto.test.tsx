import { render, screen } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { describe, expect, it, vi } from 'vitest';

vi.mock('@/components/ImageCropDialog', () => ({
  ImageCropDialog: ({ file, onCrop }: { file: File; onCrop: (blob: Blob) => Promise<void> }) => (
    <div data-testid="crop-dialog" data-filename={file.name}>
      <button
        type="button"
        onClick={() => void onCrop(new Blob(['cropped'], { type: 'image/png' }))}
      >
        confirm crop
      </button>
    </div>
  ),
}));

vi.mock('@/components/PhotoLibraryDialog', () => ({
  PhotoLibraryDialog: ({
    onSelect,
  }: {
    onSelect: (file: File, opts: { crop: boolean }) => void;
  }) => (
    <div data-testid="picker-dialog">
      <button
        type="button"
        onClick={() => {
          onSelect(new File(['lib'], 'sprout.gif', { type: 'image/gif' }), { crop: false });
        }}
      >
        pick library gif
      </button>
      <button
        type="button"
        onClick={() => {
          onSelect(new File(['up'], 'photo.png', { type: 'image/png' }), { crop: true });
        }}
      >
        pick upload
      </button>
    </div>
  ),
}));

import { EventFormPhoto } from './EventFormPhoto';

describe('EventFormPhoto', () => {
  it('opens the tabbed picker from the change-photo button', async () => {
    const user = userEvent.setup();
    render(<EventFormPhoto photoUrl="" photoUpdatedAt={null} onCrop={vi.fn()} />);

    expect(screen.queryByTestId('picker-dialog')).not.toBeInTheDocument();
    await user.click(screen.getByRole('button', { name: 'add event photo' }));
    expect(screen.getByTestId('picker-dialog')).toBeInTheDocument();
  });

  it('uploads a library pick directly, skipping the crop dialog so animation survives', async () => {
    const user = userEvent.setup();
    const onCrop = vi.fn().mockResolvedValue(undefined);
    render(<EventFormPhoto photoUrl="" photoUpdatedAt={null} onCrop={onCrop} />);

    await user.click(screen.getByRole('button', { name: 'add event photo' }));
    await user.click(screen.getByRole('button', { name: 'pick library gif' }));

    expect(screen.queryByTestId('picker-dialog')).not.toBeInTheDocument();
    expect(screen.queryByTestId('crop-dialog')).not.toBeInTheDocument();
    expect(onCrop).toHaveBeenCalledOnce();
    const uploaded = onCrop.mock.calls[0]![0] as File;
    expect(uploaded).toBeInstanceOf(File);
    expect(uploaded.name).toBe('sprout.gif');
    expect(uploaded.type).toBe('image/gif');
  });

  it('routes an upload-tab pick through the crop dialog', async () => {
    const user = userEvent.setup();
    const onCrop = vi.fn().mockResolvedValue(undefined);
    render(<EventFormPhoto photoUrl="" photoUpdatedAt={null} onCrop={onCrop} />);

    await user.click(screen.getByRole('button', { name: 'add event photo' }));
    await user.click(screen.getByRole('button', { name: 'pick upload' }));

    expect(screen.queryByTestId('picker-dialog')).not.toBeInTheDocument();
    expect(screen.getByTestId('crop-dialog')).toHaveAttribute('data-filename', 'photo.png');
    await user.click(screen.getByRole('button', { name: 'confirm crop' }));
    expect(onCrop).toHaveBeenCalledOnce();
  });
});
