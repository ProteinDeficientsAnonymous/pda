import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { render, screen } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { MemoryRouter } from 'react-router-dom';
import { describe, expect, it, vi } from 'vitest';

import type * as EventWritesModule from '@/api/eventWrites';
import { type OfficialEventDefaults, officialEventDefaultsKeys } from '@/api/officialEventDefaults';
import { QuestionType } from '@/api/questionTypes';
import { useAuthStore } from '@/auth/store';
import { Permission } from '@/models/permissions';
import { makeUser } from '@/test/fixtures';

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

vi.mock('./EventFormPhoto', () => ({ EventFormPhoto: () => null }));

import { EventForm } from './EventForm';

const defaults: OfficialEventDefaults = {
  cashappLink: 'https://cash.app/$pdanyc',
  rsvpQuestions: [
    { label: 'paid?', fieldType: QuestionType.Select, options: ['Yes'], required: true },
  ],
};

function renderForm() {
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
        <EventForm />
      </MemoryRouter>
    </QueryClientProvider>,
  );
}

describe('EventForm official defaults', () => {
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
});
