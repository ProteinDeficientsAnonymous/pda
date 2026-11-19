import { screen } from '@testing-library/react';
import { describe, expect, it } from 'vitest';

import type { PlanningSlot } from '@/api/planning';
import { makeSlot } from '@/test/fixtures';
import { renderWithProviders } from '@/test/render';

import { SlotEventLink } from './SlotEventLink';

function renderLink(s: PlanningSlot, canCreate = true) {
  renderWithProviders(<SlotEventLink slot={s} year={2027} canCreate={canCreate} />);
}

describe('SlotEventLink', () => {
  it.each([
    ['active', 'scheduled'],
    ['draft', 'draft'],
    ['cancelled', 'cancelled'],
  ] as const)('links a %s event and says %s', (eventStatus, text) => {
    renderLink(makeSlot({ eventId: 'e1', eventSlug: 'march-walk', eventStatus }), false);
    expect(screen.getByRole('link', { name: 'view event' })).toHaveAttribute(
      'href',
      '/events/march-walk',
    );
    expect(screen.getByText(`${text} ·`, { exact: false })).toBeInTheDocument();
  });

  it('renders a status-free button link when asButton', () => {
    renderWithProviders(
      <SlotEventLink
        slot={makeSlot({ eventId: 'e1', eventSlug: 'march-walk', eventStatus: 'draft' })}
        year={2027}
        canCreate={false}
        asButton
      />,
    );
    expect(screen.getByRole('link', { name: 'view event' })).toHaveAttribute(
      'href',
      '/events/march-walk',
    );
    expect(screen.queryByText(/draft/)).not.toBeInTheDocument();
  });

  it('links to the create form for the slot when there is no event', () => {
    renderLink(makeSlot());
    expect(screen.getByRole('link', { name: 'create event' })).toHaveAttribute(
      'href',
      '/events/add?planningSlot=s1&year=2027',
    );
  });

  it('shows nothing when the viewer cannot create it', () => {
    renderLink(makeSlot(), false);
    expect(screen.queryByRole('link')).not.toBeInTheDocument();
  });
});
