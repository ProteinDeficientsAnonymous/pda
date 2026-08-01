import { render, screen } from '@testing-library/react';
import { describe, expect, it } from 'vitest';

import { EventType } from '@/models/event';
import { makeEvent } from '@/test/fixtures';

import { EventBadge } from './EventBadge';

describe('EventBadge', () => {
  it('renders an official badge', () => {
    render(<EventBadge event={makeEvent({ eventType: EventType.Official })} />);
    expect(screen.getByText('official')).toBeInTheDocument();
  });

  it('renders a club badge', () => {
    render(<EventBadge event={makeEvent({ eventType: EventType.Club })} />);
    expect(screen.getByText('pda club')).toBeInTheDocument();
  });

  it.each([
    ['official', EventType.Official],
    ['pda club', EventType.Club],
  ])('uses a contrasting overlay for %s on a card', (label, eventType) => {
    render(<EventBadge event={makeEvent({ eventType })} onCard />);
    const badge = screen.getByText(label);
    expect(badge).toHaveClass('bg-black/10', 'dark:bg-white/15');
    expect(badge).not.toHaveAttribute('style');
  });
});
