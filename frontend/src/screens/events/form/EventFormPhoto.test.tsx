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
  PhotoLibraryDialog: ({ onSelect }: { onSelect: (file: File) => void }) => (
    <div data-testid="library-dialog">
      <button
        type="button"
        onClick={() => {
          onSelect(new File(['lib'], 'sprout.svg', { type: 'image/svg+xml' }));
        }}
      >
        pick sprout
      </button>
    </div>
  ),
}));

import { EventFormPhoto } from './EventFormPhoto';

describe('EventFormPhoto library picker', () => {
  it('offers a choose from library option alongside upload', () => {
    render(<EventFormPhoto photoUrl="" photoUpdatedAt={null} onCrop={vi.fn()} />);

    expect(screen.getByRole('button', { name: 'add event photo' })).toBeInTheDocument();
    expect(screen.getByRole('button', { name: 'choose from library' })).toBeInTheDocument();
  });

  it('opens the library dialog and feeds the picked image into the same crop dialog', async () => {
    const user = userEvent.setup();
    render(<EventFormPhoto photoUrl="" photoUpdatedAt={null} onCrop={vi.fn()} />);

    await user.click(screen.getByRole('button', { name: 'choose from library' }));
    expect(screen.getByTestId('library-dialog')).toBeInTheDocument();

    await user.click(screen.getByRole('button', { name: 'pick sprout' }));

    expect(screen.queryByTestId('library-dialog')).not.toBeInTheDocument();
    expect(screen.getByTestId('crop-dialog')).toHaveAttribute('data-filename', 'sprout.svg');
  });

  it('runs the library selection through the same onCrop upload pipeline as an upload', async () => {
    const user = userEvent.setup();
    const onCrop = vi.fn().mockResolvedValue(undefined);
    render(<EventFormPhoto photoUrl="" photoUpdatedAt={null} onCrop={onCrop} />);

    await user.click(screen.getByRole('button', { name: 'choose from library' }));
    await user.click(screen.getByRole('button', { name: 'pick sprout' }));
    await user.click(screen.getByRole('button', { name: 'confirm crop' }));

    expect(onCrop).toHaveBeenCalledOnce();
    expect(onCrop.mock.calls[0]![0]).toBeInstanceOf(Blob);
  });
});
