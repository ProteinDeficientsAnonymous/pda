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
});
