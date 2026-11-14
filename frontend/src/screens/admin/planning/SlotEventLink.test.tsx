import { screen } from '@testing-library/react';
import { beforeEach, describe, expect, it } from 'vitest';

import type { PlanningSlot } from '@/api/planning';
import { useAuthStore } from '@/auth/store';
import { Permission } from '@/models/permissions';
import { makeUser, makeUserWithPermissions } from '@/test/fixtures';
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

beforeEach(() => {
  useAuthStore.setState({
    user: makeUserWithPermissions([Permission.TagOfficialEvent]),
    status: 'authed',
  });
});

describe('SlotEventLink', () => {
  it('links to the event when the slot has one', () => {
    renderLink(slot({ eventId: 'e1', eventSlug: 'march-walk' }), false);
    expect(screen.getByRole('link', { name: 'view event' })).toHaveAttribute(
      'href',
      '/events/march-walk',
    );
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

  it('shows nothing without the official-event permission', () => {
    useAuthStore.setState({ user: makeUser(), status: 'authed' });
    renderLink(slot());
    expect(screen.queryByRole('link')).not.toBeInTheDocument();
  });
});
