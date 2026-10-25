import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { render, screen } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { MemoryRouter } from 'react-router-dom';
import { beforeEach, describe, expect, it, vi } from 'vitest';

import { useAuthStore } from '@/auth/store';
import { type Event, EventType } from '@/models/event';
import { Permission } from '@/models/permissions';
import { makeEvent, makeUser } from '@/test/fixtures';

vi.mock('@/api/eventDescriptionTemplates', () => ({
  useEventDescriptionTemplates: () => ({
    data: { officialWalk: 'walk copy', officialNonWalk: 'non-walk copy' },
  }),
}));

vi.mock('@/api/eventTags', () => ({
  useEventTags: () => ({
    data: [],
    isPending: false,
    isError: false,
  }),
}));

vi.mock('./EventFormPhoto', () => ({ EventFormPhoto: () => null }));

import { EventForm } from './EventForm';

function renderForm(existing?: Event) {
  const qc = new QueryClient({ defaultOptions: { queries: { retry: false } } });
  render(
    <QueryClientProvider client={qc}>
      <MemoryRouter>
        <EventForm existing={existing} />
      </MemoryRouter>
    </QueryClientProvider>,
  );
}

describe('EventForm official description template', () => {
  beforeEach(() => {
    useAuthStore.setState({
      user: makeUser({
        id: 'host',
        roles: [
          {
            id: 'r1',
            name: 'planner',
            isDefault: false,
            permissions: [Permission.TagOfficialEvent],
          },
        ],
      }),
      status: 'authed',
    });
  });

  it('fills the walk template when official is toggled on, then swaps to non-walk', async () => {
    renderForm();
    await userEvent.click(screen.getByLabelText('make it an official pda event'));
    expect(screen.getByLabelText('description')).toHaveValue('walk copy');

    await userEvent.click(screen.getByLabelText("it's a walk"));
    expect(screen.getByLabelText('description')).toHaveValue('non-walk copy');

    await userEvent.click(screen.getByLabelText("it's a walk"));
    expect(screen.getByLabelText('description')).toHaveValue('walk copy');
  });

  it('keeps a description the planner already wrote', async () => {
    renderForm();
    await userEvent.type(screen.getByLabelText('description'), 'my own words');
    await userEvent.click(screen.getByLabelText('make it an official pda event'));
    expect(screen.getByLabelText('description')).toHaveValue('my own words');
  });

  it('does not refill after the planner clears the template', async () => {
    renderForm();
    await userEvent.click(screen.getByLabelText('make it an official pda event'));
    await userEvent.clear(screen.getByLabelText('description'));
    expect(screen.getByLabelText('description')).toHaveValue('');
  });

  it('leaves existing events alone', async () => {
    renderForm(makeEvent({ eventType: EventType.Community, description: '' }));
    await userEvent.click(screen.getByLabelText('make it an official pda event'));
    expect(screen.getByLabelText('description')).toHaveValue('');
  });
});
