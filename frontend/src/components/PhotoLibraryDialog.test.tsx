import { render, screen } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { beforeEach, describe, expect, it, vi } from 'vitest';

import { EVENT_LIBRARY_IMAGES } from '@/assets/eventLibraryImages';

import { PhotoLibraryDialog } from './PhotoLibraryDialog';

beforeEach(() => {
  vi.stubGlobal(
    'fetch',
    vi.fn().mockResolvedValue({
      blob: () => Promise.resolve(new Blob(['img'], { type: 'image/svg+xml' })),
    }),
  );
});

describe('PhotoLibraryDialog', () => {
  it('renders every curated library image as a pickable option', () => {
    render(<PhotoLibraryDialog onCancel={vi.fn()} onSelect={vi.fn()} />);

    for (const image of EVENT_LIBRARY_IMAGES) {
      expect(screen.getByRole('button', { name: image.label })).toBeInTheDocument();
    }
  });

  it('converts the picked image into a File and calls onSelect', async () => {
    const user = userEvent.setup();
    const onSelect = vi.fn();
    render(<PhotoLibraryDialog onCancel={vi.fn()} onSelect={onSelect} />);

    await user.click(screen.getByRole('button', { name: EVENT_LIBRARY_IMAGES[0]!.label }));

    expect(onSelect).toHaveBeenCalledOnce();
    const file = onSelect.mock.calls[0]![0] as File;
    expect(file).toBeInstanceOf(File);
    expect(file.type).toBe('image/svg+xml');
  });

  it('cancel button calls onCancel', async () => {
    const user = userEvent.setup();
    const onCancel = vi.fn();
    render(<PhotoLibraryDialog onCancel={onCancel} onSelect={vi.fn()} />);

    await user.click(screen.getByRole('button', { name: /^cancel$/i }));

    expect(onCancel).toHaveBeenCalledOnce();
  });

  it('dialog container has role="dialog" and is accessible', () => {
    render(<PhotoLibraryDialog onCancel={vi.fn()} onSelect={vi.fn()} />);

    const dialog = screen.getByRole('dialog');
    expect(dialog).toHaveAttribute('aria-modal', 'true');
    expect(dialog).toHaveAttribute('aria-label', 'choose from library');
  });
});
