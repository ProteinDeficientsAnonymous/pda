import { screen } from '@testing-library/react';
import { describe, expect, it } from 'vitest';

import { renderWithProviders } from '@/test/render';

import { EventForbiddenNotice } from './EventForbiddenNotice';

describe('EventForbiddenNotice', () => {
  it('links back to the event', () => {
    renderWithProviders(<EventForbiddenNotice eventId="ev1" message="hosts only" />);

    expect(screen.getByText('hosts only')).toBeInTheDocument();
    expect(screen.getByRole('link', { name: 'back to event' })).toHaveAttribute(
      'href',
      '/events/ev1',
    );
  });

  it('falls back to the calendar without an event id', () => {
    renderWithProviders(<EventForbiddenNotice eventId={undefined} message="hosts only" />);

    expect(screen.getByRole('link', { name: 'back to event' })).toHaveAttribute(
      'href',
      '/calendar',
    );
  });
});
