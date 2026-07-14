import { fireEvent, render, screen } from '@testing-library/react';
import { describe, expect, it, vi } from 'vitest';

import { RsvpStatusPicker } from './RsvpStatusPicker';

describe('RsvpStatusPicker', () => {
  it('renders the three pills with default labels', () => {
    render(<RsvpStatusPicker value={null} onSelect={vi.fn()} />);
    expect(screen.getByRole('button', { name: "i'm going" })).toBeInTheDocument();
    expect(screen.getByRole('button', { name: 'maybe' })).toBeInTheDocument();
    expect(screen.getByRole('button', { name: "can't go" })).toBeInTheDocument();
  });

  it('marks the active pill via aria-pressed', () => {
    render(<RsvpStatusPicker value="maybe" onSelect={vi.fn()} />);
    expect(screen.getByRole('button', { name: 'maybe' })).toHaveAttribute('aria-pressed', 'true');
    expect(screen.getByRole('button', { name: "i'm going" })).toHaveAttribute(
      'aria-pressed',
      'false',
    );
  });

  it('calls onSelect with the status and does not toggle off the active pill', () => {
    const onSelect = vi.fn();
    render(<RsvpStatusPicker value="attending" onSelect={onSelect} />);
    fireEvent.click(screen.getByRole('button', { name: "i'm going" }));
    expect(onSelect).toHaveBeenCalledWith('attending');
  });

  it('lays the pills out in a single horizontally scrollable row', () => {
    render(<RsvpStatusPicker value={null} onSelect={vi.fn()} />);
    const row = screen.getByRole('button', { name: 'maybe' }).parentElement;
    expect(row).toHaveClass('overflow-x-auto');
    expect(row).not.toHaveClass('flex-wrap');
    expect(row).toHaveClass('justify-center-safe');
  });

  it('keeps each pill from shrinking so labels are never truncated', () => {
    render(<RsvpStatusPicker value={null} onSelect={vi.fn()} />);
    expect(screen.getByRole('button', { name: "i'm going" })).toHaveClass('shrink-0');
  });

  it('applies labelFor overrides', () => {
    render(
      <RsvpStatusPicker
        value={null}
        onSelect={vi.fn()}
        labelFor={(s, def) => (s === 'attending' ? 'join the waitlist' : def)}
      />,
    );
    expect(screen.getByRole('button', { name: 'join the waitlist' })).toBeInTheDocument();
  });
});
