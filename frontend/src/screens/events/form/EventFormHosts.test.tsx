import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { fireEvent, render, screen } from '@testing-library/react';
import { MemoryRouter } from 'react-router-dom';
import { beforeEach, describe, expect, it, vi } from 'vitest';

import type * as EventWritesModule from '@/api/eventWrites';
import { useAuthStore } from '@/auth/store';
import type { Event } from '@/models/event';
import type { User } from '@/models/user';
import { makeEvent } from '@/test/fixtures';

type EventWrites = typeof EventWritesModule;

vi.mock('@/api/cohostInvites', () => ({
  useAcceptCohostInvite: () => ({ mutate: vi.fn(), isPending: false }),
  useDeclineCohostInvite: () => ({ mutate: vi.fn(), isPending: false }),
  useRescindCohostInvite: () => ({ mutate: vi.fn(), isPending: false }),
  useRemoveCohost: () => ({ mutate: vi.fn(), isPending: false }),
  useAddCohosts: () => ({ mutateAsync: vi.fn(), isPending: false }),
}));

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

const HOST: User = {
  id: 'creator',
  fullName: 'creator person',
  phoneNumber: '+15551110000',
  photoUrl: '',
  roles: [],
  permissions: [],
} as unknown as User;

function renderForm(existing?: Event) {
  const qc = new QueryClient({ defaultOptions: { queries: { retry: false } } });
  const result = render(
    <QueryClientProvider client={qc}>
      <MemoryRouter>
        <EventForm existing={existing} />
      </MemoryRouter>
    </QueryClientProvider>,
  );
  // The hosts card is collapsed by default — its contents aren't mounted until opened.
  fireEvent.click(screen.getByRole('button', { name: /hosts/ }));
  return result;
}

describe('EventForm hosts section', () => {
  beforeEach(() => {
    vi.clearAllMocks();
    useAuthStore.setState({ user: HOST, status: 'authed' });
  });

  it('shows current co-host chips on edit instead of the staged picker', () => {
    renderForm(
      makeEvent({
        coHostIds: ['creator', 'u2'],
        coHostNames: ['creator person', 'jamie'],
        coHostPhotoUrls: ['', ''],
      }),
    );

    expect(screen.getByText('jamie')).toBeInTheDocument();
    expect(screen.getByRole('button', { name: 'add co-host' })).toBeInTheDocument();
    expect(screen.queryByLabelText('co-hosts')).not.toBeInTheDocument();
  });

  it('offers removal of an existing co-host from the edit form', () => {
    renderForm(
      makeEvent({
        coHostIds: ['creator', 'u2'],
        coHostNames: ['creator person', 'jamie'],
        coHostPhotoUrls: ['', ''],
      }),
    );

    expect(screen.getByRole('button', { name: 'remove jamie as co-host' })).toBeInTheDocument();
  });

  it('shows the staged member picker when creating', () => {
    renderForm();

    expect(screen.getByLabelText('co-hosts')).toBeInTheDocument();
    expect(screen.queryByRole('button', { name: 'add co-host' })).not.toBeInTheDocument();
  });
});
