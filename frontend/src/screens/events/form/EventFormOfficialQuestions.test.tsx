import { screen } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { beforeEach, describe, expect, it, vi } from 'vitest';

import type * as EventWritesModule from '@/api/eventWrites';
import { useAuthStore } from '@/auth/store';
import { Permission } from '@/models/permissions';
import { makeUser } from '@/test/fixtures';
import { renderWithProviders } from '@/test/render';

type EventWrites = typeof EventWritesModule;

vi.mock('@/api/eventWrites', async () => {
  const actual = await vi.importActual<EventWrites>('@/api/eventWrites');
  return {
    ...actual,
    useCreateEvent: () => ({ mutateAsync: vi.fn(), isPending: false }),
    useUpdateEvent: () => ({ mutateAsync: vi.fn(), isPending: false }),
    useUploadEventPhoto: () => ({ mutateAsync: vi.fn(), isPending: false }),
  };
});

vi.mock('@/api/eventDescriptionTemplates', () => ({
  useEventDescriptionTemplates: () => ({ data: undefined }),
}));

vi.mock('@/api/officialEventDefaults', () => ({
  useOfficialEventDefaults: () => ({
    data: {
      cashappLink: '$pdanyc',
      rsvpQuestions: [
        { label: 'pronouns?', fieldType: 'text', options: [], required: false },
        { label: 'first walk?', fieldType: 'checkbox', options: [], required: false },
      ],
    },
  }),
}));

vi.mock('./EventFormPhoto', () => ({ EventFormPhoto: () => null }));

import { EventForm } from './EventForm';

function renderForm() {
  renderWithProviders(<EventForm />);
}

describe('EventForm official questions', () => {
  beforeEach(() => {
    useAuthStore.setState({
      user: makeUser({
        roles: [
          {
            id: 'role-official',
            name: 'organizer',
            isDefault: false,
            permissions: [Permission.TagOfficialEvent],
          },
        ],
      }),
      status: 'authed',
    });
  });

  it('adds the official rsvp questions when the event becomes official and drops them after', async () => {
    renderForm();
    const toggle = screen.getByRole('switch', { name: 'make it an official pda event' });

    await userEvent.click(toggle);
    expect(screen.getByText('2 questions')).toBeInTheDocument();

    await userEvent.click(toggle);
    expect(screen.queryByText('2 questions')).not.toBeInTheDocument();
  });
});
