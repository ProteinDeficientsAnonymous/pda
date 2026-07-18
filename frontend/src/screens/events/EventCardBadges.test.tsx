import { render, screen } from '@testing-library/react';
import { describe, expect, it } from 'vitest';

import { RsvpServerStatus } from '@/models/event';
import { makeEvent } from '@/test/fixtures';

import { EventCardBadges } from './EventCardBadges';

describe('EventCardBadges', () => {
  it('renders nothing when there is no rsvp and capacity is unlimited', () => {
    const { container } = render(<EventCardBadges event={makeEvent()} variant="card" />);
    expect(container).toBeEmptyDOMElement();
  });

  it('shows the viewer rsvp state', () => {
    render(
      <EventCardBadges event={makeEvent({ myRsvp: RsvpServerStatus.Attending })} variant="card" />,
    );
    expect(screen.getByText('going')).toBeInTheDocument();
  });

  it('shows going/{max} headcount for capacity-limited events', () => {
    render(
      <EventCardBadges event={makeEvent({ maxAttendees: 20, attendingCount: 8 })} variant="row" />,
    );
    expect(screen.getByText('8 / 20 going')).toBeInTheDocument();
  });

  it('omits the headcount for unlimited-capacity events', () => {
    render(
      <EventCardBadges
        event={makeEvent({ maxAttendees: null, myRsvp: RsvpServerStatus.Maybe })}
        variant="row"
      />,
    );
    expect(screen.getByText('maybe')).toBeInTheDocument();
    expect(screen.queryByText(/going$/)).not.toBeInTheDocument();
  });
});
