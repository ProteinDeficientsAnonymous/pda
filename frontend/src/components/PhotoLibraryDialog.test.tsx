import { render, screen, waitFor } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { beforeEach, describe, expect, it, vi } from 'vitest';

import * as giphyApi from '@/api/giphy';

import { PhotoLibraryDialog } from './PhotoLibraryDialog';

vi.mock('@/api/giphy');

const GIFS = [
  {
    id: 'a1',
    title: 'sprout dance',
    previewUrl: 'https://example.com/a1-small.gif',
    originalUrl: 'https://example.com/a1.gif',
    source: 'gif' as const,
  },
  {
    id: 'a2',
    title: 'carrot spin',
    previewUrl: 'https://example.com/a2-small.png',
    originalUrl: 'https://example.com/a2.png',
    source: 'photo' as const,
  },
];

beforeEach(() => {
  vi.mocked(giphyApi.searchGifs).mockResolvedValue(GIFS);
  vi.stubGlobal(
    'fetch',
    vi.fn().mockResolvedValue({
      blob: () => Promise.resolve(new Blob(['gif'], { type: 'image/gif' })),
    }),
  );
});

describe('PhotoLibraryDialog', () => {
  it('loads default gifs on mount before any search', async () => {
    render(<PhotoLibraryDialog onCancel={vi.fn()} onSelect={vi.fn()} />);

    await waitFor(() => {
      expect(giphyApi.searchGifs).toHaveBeenCalledWith('');
    });
    expect(await screen.findByRole('button', { name: 'sprout dance' })).toBeInTheDocument();
    expect(screen.getByRole('button', { name: 'carrot spin' })).toBeInTheDocument();
  });

  it('searches gifs as the user types and renders results', async () => {
    const user = userEvent.setup();
    render(<PhotoLibraryDialog onCancel={vi.fn()} onSelect={vi.fn()} />);

    await user.type(screen.getByPlaceholderText('search gifs and photos'), 'sprout');

    await waitFor(() => {
      expect(giphyApi.searchGifs).toHaveBeenCalledWith('sprout');
    });
    expect(await screen.findByRole('button', { name: 'sprout dance' })).toBeInTheDocument();
    expect(screen.getByRole('button', { name: 'carrot spin' })).toBeInTheDocument();
  });

  it('converts the picked gif into a File and calls onSelect', async () => {
    const user = userEvent.setup();
    const onSelect = vi.fn();
    render(<PhotoLibraryDialog onCancel={vi.fn()} onSelect={onSelect} />);

    await user.type(screen.getByPlaceholderText('search gifs and photos'), 'sprout');
    await user.click(await screen.findByRole('button', { name: 'sprout dance' }));

    expect(onSelect).toHaveBeenCalledOnce();
    const file = onSelect.mock.calls[0]![0] as File;
    expect(file).toBeInstanceOf(File);
    expect(file.name).toBe('a1.gif');
    expect(file.type).toBe('image/gif');
  });

  it('converts a picked photo into a file with the correct extension', async () => {
    vi.stubGlobal(
      'fetch',
      vi.fn().mockResolvedValue({
        blob: () => Promise.resolve(new Blob(['photo'], { type: 'image/jpeg' })),
      }),
    );
    const user = userEvent.setup();
    const onSelect = vi.fn();
    render(<PhotoLibraryDialog onCancel={vi.fn()} onSelect={onSelect} />);

    await user.click(await screen.findByRole('button', { name: 'carrot spin' }));

    const file = onSelect.mock.calls[0]![0] as File;
    expect(file.name).toBe('a2.jpeg');
    expect(file.type).toBe('image/jpeg');
  });

  it('shows an error message when search fails', async () => {
    vi.mocked(giphyApi.searchGifs).mockRejectedValue(new Error('network error'));
    const user = userEvent.setup();
    render(<PhotoLibraryDialog onCancel={vi.fn()} onSelect={vi.fn()} />);

    await user.type(screen.getByPlaceholderText('search gifs and photos'), 'sprout');

    expect(await screen.findByRole('alert')).toHaveTextContent(
      "couldn't search images — try again",
    );
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
    expect(dialog).toHaveAttribute('aria-label', 'choose an image');
  });
});
