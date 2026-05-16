import { fireEvent, render, screen } from '@testing-library/react';
import { describe, expect, it, vi } from 'vitest';

import { CommentComposer } from './CommentComposer';

describe('CommentComposer', () => {
  it('disables submit when empty', () => {
    render(<CommentComposer onSubmit={vi.fn()} submitting={false} />);
    expect(screen.getByRole('button', { name: /post/i })).toBeDisabled();
  });

  it('enables submit when non-empty', () => {
    render(<CommentComposer onSubmit={vi.fn()} submitting={false} />);
    fireEvent.change(screen.getByRole('textbox'), { target: { value: 'hi' } });
    expect(screen.getByRole('button', { name: /post/i })).toBeEnabled();
  });

  it('disables submit when over the limit', () => {
    render(<CommentComposer onSubmit={vi.fn()} submitting={false} />);
    fireEvent.change(screen.getByRole('textbox'), { target: { value: 'x'.repeat(501) } });
    expect(screen.getByRole('button', { name: /post/i })).toBeDisabled();
  });

  it('submits on cmd+enter', () => {
    const onSubmit = vi.fn();
    render(<CommentComposer onSubmit={onSubmit} submitting={false} />);
    const textbox = screen.getByRole('textbox');
    fireEvent.change(textbox, { target: { value: 'hi' } });
    fireEvent.keyDown(textbox, { key: 'Enter', metaKey: true });
    expect(onSubmit).toHaveBeenCalledWith('hi');
  });

  it('shows counter warning color near limit', () => {
    render(<CommentComposer onSubmit={vi.fn()} submitting={false} />);
    fireEvent.change(screen.getByRole('textbox'), { target: { value: 'x'.repeat(460) } });
    expect(screen.getByTestId('comment-char-counter')).toHaveAttribute(
      'data-state',
      'warning',
    );
  });
});
