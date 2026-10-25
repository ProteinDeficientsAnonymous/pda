import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { render, screen, waitFor } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { MemoryRouter } from 'react-router-dom';
import { beforeEach, describe, expect, it, vi } from 'vitest';

import { syncEventRsvpQuestions } from '@/api/eventRsvpQuestions';
import type * as EventWritesModule from '@/api/eventWrites';
import { type OfficialEventDefaults, officialEventDefaultsKeys } from '@/api/officialEventDefaults';
import { QuestionType } from '@/api/questionTypes';
import { useAuthStore } from '@/auth/store';
import { type Event, EventType } from '@/models/event';
import { Permission } from '@/models/permissions';
import { makeEvent, makeUser } from '@/test/fixtures';

type EventWrites = typeof EventWritesModule;

const { updateEvent } = vi.hoisted(() => ({ updateEvent: vi.fn() }));

vi.mock('@/api/eventWrites', async () => {
  const actual = await vi.importActual<EventWrites>('@/api/eventWrites');
  return {
    ...actual,
    useCreateEvent: () => ({ mutateAsync: vi.fn(), isPending: false }),
    useUpdateEvent: () => ({ mutateAsync: updateEvent, isPending: false }),
    useUploadEventPhoto: () => ({ mutateAsync: vi.fn(), isPending: false }),
  };
});

vi.mock('@/api/eventRsvpQuestions', async (importActual) => ({
  ...(await importActual<object>()),
  syncEventRsvpQuestions: vi.fn(async () => []),
}));
vi.mock('./EventFormPhoto', () => ({ EventFormPhoto: () => null }));

import { EventForm } from './EventForm';

const defaults: OfficialEventDefaults = {
  cashappLink: 'https://cash.app/$pdanyc',
  rsvpQuestions: [
    { label: 'paid?', fieldType: QuestionType.Select, options: ['Yes'], required: true },
  ],
};

function renderForm(existing?: Event) {
  useAuthStore.setState({
    user: makeUser({
      roles: [
        { id: 'r1', name: 'planner', isDefault: false, permissions: [Permission.TagOfficialEvent] },
      ],
    }),
    status: 'authed',
  });
  const qc = new QueryClient({ defaultOptions: { queries: { retry: false } } });
  qc.setQueryData(officialEventDefaultsKeys.all, defaults);
  render(
    <QueryClientProvider client={qc}>
      <MemoryRouter>
        <EventForm existing={existing} />
      </MemoryRouter>
    </QueryClientProvider>,
  );
}

describe('EventForm official defaults', () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  it('making an event official fills cash app and adds the official questions', async () => {
    renderForm();
    expect(screen.queryByText('paid?')).not.toBeInTheDocument();
    await userEvent.click(screen.getByRole('switch', { name: 'make it an official pda event' }));
    expect(screen.getByText('paid?')).toBeInTheDocument();
    expect(screen.getByLabelText('cash app')).toHaveValue('$pdanyc');
  });

  it('turning official off drops the untouched official questions', async () => {
    renderForm();
    const toggle = screen.getByRole('switch', { name: 'make it an official pda event' });
    await userEvent.click(toggle);
    await userEvent.click(toggle);
    expect(screen.queryByText('paid?')).not.toBeInTheDocument();
  });

  it('accepts the questions the server added when an edit makes the event official', async () => {
    const existing = makeEvent({ eventType: EventType.Community, rsvpQuestions: [] });
    const serverAdded = { id: 'srv-1', ...defaults.rsvpQuestions[0]! };
    updateEvent.mockResolvedValue({
      ...existing,
      eventType: EventType.Official,
      rsvpQuestions: [serverAdded],
    });
    renderForm(existing);
    await userEvent.click(screen.getByRole('switch', { name: 'make it an official pda event' }));
    await userEvent.click(screen.getByRole('button', { name: 'save' }));

    await waitFor(() => {
      expect(syncEventRsvpQuestions).toHaveBeenCalledWith(
        existing.id,
        [expect.objectContaining({ label: 'paid?' })],
        [serverAdded],
      );
    });
  });
});
