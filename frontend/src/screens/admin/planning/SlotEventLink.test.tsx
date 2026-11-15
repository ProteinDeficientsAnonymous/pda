import { screen } from '@testing-library/react';
import { describe, expect, it } from 'vitest';

import type { PlanningSlot } from '@/api/planning';
import { renderWithProviders } from '@/test/render';

import { SlotEventLink } from './SlotEventLink';

const slot = (over: Partial<PlanningSlot> = {}): PlanningSlot => ({
  id: 's1',
  label: 'march',
  month: 3,
  kind: 'monthly',
  order: 3,
  eventId: null,
  eventSlug: null,
  eventStatus: null,
  ...over,
});

function renderLink(s: PlanningSlot, canCreate = true) {
  renderWithProviders(<SlotEventLink slot={s} year={2027} canCreate={canCreate} />);
}

describe('SlotEventLink', () => {
  it.each([
    ['active', 'scheduled'],
    ['draft', 'draft'],
    ['cancelled', 'cancelled'],
  ] as const)('links a %s event and says %s', (eventStatus, text) => {
    renderLink(slot({ eventId: 'e1', eventSlug: 'march-walk', eventStatus }), false);
    expect(screen.getByRole('link', { name: 'view event' })).toHaveAttribute(
      'href',
      '/events/march-walk',
    );
    expect(screen.getByText(`${text} ·`, { exact: false })).toBeInTheDocument();
  });

  it('links to the create form for the slot when there is no event', () => {
    renderLink(slot());
    expect(screen.getByRole('link', { name: 'create event' })).toHaveAttribute(
      'href',
      '/events/add?planningSlot=s1&year=2027',
    );
  });

  it('shows nothing when the viewer cannot create it', () => {
    renderLink(slot(), false);
    expect(screen.queryByRole('link')).not.toBeInTheDocument();
  });
});
